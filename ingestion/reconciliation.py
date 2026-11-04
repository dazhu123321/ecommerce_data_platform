"""Read-only snapshot reconciliation for the ORDERS development lab.

The SQL operates only on allowlisted non-production lab tables.
No credentials are embedded; connection is reused from ingestion.load_table.
"""
from dataclasses import dataclass
from typing import Any

# Explicit development-only allowlist. No arbitrary identifier interpolation.
SOURCE = "ECOM_RAW.ANALYTICS_DEV.ORDERS_MERGE_LAB_SOURCE"
TARGET = "ECOM_RAW.ANALYTICS_DEV.ORDERS_MERGE_LAB_TARGET"

KEY = "ORDER_ID"
COLUMNS = (
    "ORDER_ID", "USER_ID", "STATUS", "GENDER", "CREATED_AT",
    "RETURNED_AT", "SHIPPED_AT", "DELIVERED_AT", "NUM_OF_ITEM",
)
NON_KEY_COLUMNS = tuple(c for c in COLUMNS if c != KEY)


@dataclass(frozen=True)
class ReconciliationResult:
    inserted: int
    updated: int
    unchanged: int
    missing: int
    source_rows: int
    target_rows: int

    def as_dict(self) -> dict[str, int]:
        return {
            "INSERT": self.inserted, "UPDATE": self.updated,
            "UNCHANGED": self.unchanged, "MISSING": self.missing,
            "SOURCE_ROWS": self.source_rows, "TARGET_ROWS": self.target_rows,
        }


def validate_snapshot(cursor: Any, table: str) -> int:
    """Reject empty, NULL-key and duplicate-key snapshots/targets."""
    if table not in (SOURCE, TARGET):
        raise ValueError("Only lab tables are allowed")
    cursor.execute(f"""
        SELECT COUNT(*), COUNT(DISTINCT {KEY}), COUNT_IF({KEY} IS NULL)
        FROM {table}
    """)
    row_count, unique_keys, null_keys = cursor.fetchone()
    if row_count == 0:
        raise ValueError(f"Refusing empty table: {table}")
    if null_keys != 0 or unique_keys != row_count:
        raise ValueError(
            f"Invalid primary key in {table}: "
            f"rows={row_count}, unique={unique_keys}, nulls={null_keys}"
        )
    return int(row_count)


def build_reconciliation_sql() -> str:
    changed = "\n            OR ".join(
        f"s.{column} IS DISTINCT FROM t.{column}"
        for column in NON_KEY_COLUMNS
    )
    return f"""
        WITH changes AS (
            SELECT
                CASE
                    WHEN t.{KEY} IS NULL THEN 'INSERT'
                    WHEN s.{KEY} IS NULL THEN 'MISSING'
                    WHEN {changed} THEN 'UPDATE'
                    ELSE 'UNCHANGED'
                END AS CHANGE_TYPE
            FROM {SOURCE} AS s
            FULL OUTER JOIN {TARGET} AS t
              ON s.{KEY} = t.{KEY}
        )
        SELECT CHANGE_TYPE, COUNT(*)
        FROM changes GROUP BY CHANGE_TYPE
    """


def reconcile(cursor: Any) -> ReconciliationResult:
    source_rows = validate_snapshot(cursor, SOURCE)
    target_rows = validate_snapshot(cursor, TARGET)
    cursor.execute(build_reconciliation_sql())
    counts = {"INSERT": 0, "UPDATE": 0, "UNCHANGED": 0, "MISSING": 0}
    for category, count in cursor.fetchall():
        if category not in counts:
            raise ValueError(f"Unexpected category: {category}")
        counts[category] = int(count)
    if counts["INSERT"] + counts["UPDATE"] + counts["UNCHANGED"] != source_rows:
        raise RuntimeError("Reconciliation/source row count mismatch")
    if counts["UPDATE"] + counts["UNCHANGED"] + counts["MISSING"] != target_rows:
        raise RuntimeError("Reconciliation/target row count mismatch")
    return ReconciliationResult(
        inserted=counts["INSERT"],
        updated=counts["UPDATE"],
        unchanged=counts["UNCHANGED"],
        missing=counts["MISSING"],
        source_rows=source_rows,
        target_rows=target_rows,
    )


def main() -> None:
    from ingestion.load_table import get_connection
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            result = reconcile(cursor)
        for key, value in result.as_dict().items():
            print(f"{key:14} {value:,}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
