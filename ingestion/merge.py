"""Guarded Snowflake MERGE for the ORDERS development lab.

Default mode is dry-run; --apply explicitly authorizes writes, ONLY to
the lab target allowlisted in reconciliation.py. No production paths here.
"""
import argparse
from typing import Any

from ingestion.reconciliation import (
    SOURCE, TARGET, KEY, NON_KEY_COLUMNS, COLUMNS, reconcile,
)


def build_merge_sql() -> str:
    changed = "\n        OR ".join(
        f"s.{col} IS DISTINCT FROM t.{col}" for col in NON_KEY_COLUMNS
    )
    # Explicit assignments avoid physical-column-order bugs.
    assignments = ",\n        ".join(
        f"t.{col} = s.{col}" for col in NON_KEY_COLUMNS
    )
    cols = ", ".join(COLUMNS)
    values = ", ".join(f"s.{col}" for col in COLUMNS)
    return f"""
        MERGE INTO {TARGET} AS t
        USING {SOURCE} AS s
          ON t.{KEY} = s.{KEY}
        WHEN MATCHED AND (
            {changed}
        ) THEN UPDATE SET
            {assignments}
        WHEN NOT MATCHED THEN
            INSERT ({cols}) VALUES ({values})
    """


def run_merge(conn: Any, apply: bool = False) -> dict[str, object]:
    """Preflight in dry-run; apply only with explicit authorization."""
    with conn.cursor() as cursor:
        before = reconcile(cursor)
        print(f"Preflight: {before.as_dict()}")
        if not apply:
            print("DRY RUN ONLY. No tables were modified.")
            return {"applied": False, "before": before}
        # Recheck state and execute in same Snowflake transaction.
        cursor.execute("BEGIN")
        try:
            before = reconcile(cursor)
            cursor.execute(build_merge_sql())
            merge_result = cursor.fetchone()  # Snowflake DML result counts
            after = reconcile(cursor)
            if after.inserted != 0 or after.updated != 0:
                raise RuntimeError(
                    "Post-MERGE reconciliation still has INSERT/UPDATE differences"
                )
            if after.missing != before.missing:
                raise RuntimeError("MERGE unexpectedly changed missing-key count")
            conn.commit()
            return {
                "applied": True,
                "before": before,
                "after": after,
                "snowflake_result": merge_result,
            }
        except Exception:
            conn.rollback()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="ORDERS lab MERGE only")
    parser.add_argument(
        "--apply", action="store_true",
        help="Execute MERGE against ANALYTICS_DEV lab target"
    )
    args = parser.parse_args()
    from ingestion.load_table import get_connection
    conn = get_connection()
    try:
        result = run_merge(conn, apply=args.apply)
        print(result)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
