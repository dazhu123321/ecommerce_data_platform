"""Generic, guarded Snowflake MERGE for development lab tables.

Usage:
    python -m ingestion.generic_merge --table orders
    python -m ingestion.generic_merge --table orders --apply

Default: DRY RUN (no database writes).
"""

import argparse
from typing import Any

from ingestion.generic_reconciliation import (
    TablePair,
    lab_pair,
    reconcile_pair,
)


def build_merge_sql(pair: TablePair) -> str:
    """Generate INSERT + UPDATE MERGE SQL without DELETE."""

    # Do not accept arbitrary source/target table names.
    if pair != lab_pair(pair.name.lower()):
        raise ValueError("Only canonical development lab tables are allowed")

    key = pair.primary_key
    columns = pair.columns

    if key not in columns:
        raise ValueError("Primary key missing from columns")

    compare_columns = [c for c in columns if c != key]

    if not compare_columns:
        raise ValueError("No columns available for UPDATE")

    changed_condition = "\n        OR ".join(
        f"s.{col} IS DISTINCT FROM t.{col}"
        for col in compare_columns
    )

    update_assignments = ",\n        ".join(
        f"{col} = s.{col}"
        for col in compare_columns
    )

    insert_columns = ", ".join(columns)

    insert_values = ", ".join(
        f"s.{col}" for col in columns
    )

    return f"""
MERGE INTO {pair.target} AS t
USING {pair.source} AS s

ON t.{key} = s.{key}

WHEN MATCHED AND (
    {changed_condition}
)
THEN UPDATE SET
    {update_assignments}

WHEN NOT MATCHED
THEN INSERT ({insert_columns})
VALUES ({insert_values})
"""


def run_merge(
    conn: Any,
    table_name: str,
    apply: bool = False,
) -> dict:
    """Run reconciliation and optionally apply the lab MERGE."""

    pair = lab_pair(table_name)

    # For now only ORDERS is integration-tested.
    if apply and table_name != "orders":
        raise ValueError(
            "Write access is currently enabled only for "
            "the tested ORDERS development lab"
        )

    cursor = conn.cursor()

    try:
        # Dry-run is strictly read-only.
        if not apply:
            before = reconcile_pair(cursor, pair)

            print("Before MERGE:")
            print(before)
            print("DRY RUN ONLY. No tables were modified.")

            return {
                "applied": False,
                "before": before,
            }

        # Explicit Snowflake transaction.
        cursor.execute("BEGIN TRANSACTION")

        try:
            before = reconcile_pair(cursor, pair)

            print("Before MERGE:")
            print(before)

            sql = build_merge_sql(pair)
            cursor.execute(sql)

            result = cursor.fetchone()

            after = reconcile_pair(cursor, pair)

            # All source rows should now match target rows.
            if after["INSERT"] != 0:
                raise RuntimeError(
                    "Post-MERGE validation failed: INSERT remains"
                )

            if after["UPDATE"] != 0:
                raise RuntimeError(
                    "Post-MERGE validation failed: UPDATE remains"
                )

            # MERGE must preserve missing target records.
            if after["MISSING"] != before["MISSING"]:
                raise RuntimeError(
                    "Unexpected MISSING count change"
                )

            cursor.execute("COMMIT")

            print("MERGE completed successfully.")
            print("Snowflake MERGE result:", result)
            print("After MERGE:", after)

            return {
                "applied": True,
                "before": before,
                "after": after,
                "snowflake_result": result,
            }

        except Exception:
            cursor.execute("ROLLBACK")
            raise

    finally:
        cursor.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generic Snapshot MERGE - Development Lab"
    )

    parser.add_argument(
        "--table",
        required=True,
        choices=["orders", "order_items", "users", "products"],
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply MERGE to an approved development lab table",
    )

    args = parser.parse_args()

    from ingestion.load_table import get_connection

    conn = get_connection()

    try:
        result = run_merge(
            conn,
            table_name=args.table,
            apply=args.apply,
        )

        print(result)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
