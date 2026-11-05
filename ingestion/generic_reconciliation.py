
"""Generic snapshot reconciliation for four e-commerce tables.

Read-only operations on development lab tables.
"""

from dataclasses import dataclass
from typing import Any

from ingestion.table_config import get_table_config


@dataclass(frozen=True)
class TablePair:
    name: str
    source: str
    target: str
    primary_key: str
    columns: tuple[str, ...]


def lab_pair(table_name: str) -> TablePair:
    """Build an allowlisted development table pair."""

    allowed = ("orders", "order_items", "users", "products")

    if table_name not in allowed:
        raise ValueError(f"Unsupported table: {table_name}")

    config = get_table_config(table_name)
    name = config.name.upper()

    return TablePair(
        name=name,
        source=f"ECOM_RAW.ANALYTICS_DEV.{name}_MERGE_LAB_SOURCE",
        target=f"ECOM_RAW.ANALYTICS_DEV.{name}_MERGE_LAB_TARGET",
        primary_key=config.primary_key.upper(),
        columns=tuple(c.upper() for c in config.columns),
    )


def build_reconciliation_sql(pair: TablePair) -> str:
    """Generate snapshot comparison SQL."""

    key = pair.primary_key

    if key not in pair.columns:
        raise ValueError(f"Primary key missing: {key}")

    comparisons = [
        f"s.{col} IS DISTINCT FROM t.{col}"
        for col in pair.columns
        if col != key
    ]

    if not comparisons:
        raise ValueError("No columns available for comparison")

    changed_condition = "\n OR ".join(comparisons)

    return f"""
    WITH reconciliation AS (
        SELECT
            CASE
                WHEN t.{key} IS NULL THEN 'INSERT'
                WHEN s.{key} IS NULL THEN 'MISSING'
                WHEN {changed_condition} THEN 'UPDATE'
                ELSE 'UNCHANGED'
            END AS CHANGE_TYPE

        FROM {pair.source} AS s

        FULL OUTER JOIN {pair.target} AS t
            ON s.{key} = t.{key}
    )

    SELECT
        CHANGE_TYPE,
        COUNT(*) AS RECORD_COUNT

    FROM reconciliation

    GROUP BY CHANGE_TYPE
    ORDER BY CHANGE_TYPE
    """


def validate_key(
    cursor: Any,
    table: str,
    key: str,
) -> int:
    """Validate primary key uniqueness and non-empty data."""

    cursor.execute(f"""
        SELECT
            COUNT(*),
            COUNT(DISTINCT {key}),
            COUNT_IF({key} IS NULL)
        FROM {table}
    """)

    total_rows, unique_ids, null_ids = map(
        int, cursor.fetchone()
    )

    if total_rows == 0:
        raise ValueError(f"Empty table: {table}")

    if unique_ids != total_rows or null_ids != 0:
        raise ValueError(
            f"Invalid primary keys in {table}: "
            f"total={total_rows}, "
            f"unique={unique_ids}, "
            f"null={null_ids}"
        )

    return total_rows


def reconcile_pair(
    cursor: Any,
    pair: TablePair,
) -> dict[str, int]:
    """Run read-only reconciliation on lab tables."""

    if pair != lab_pair(pair.name.lower()):
        raise ValueError(
            "Only canonical development lab tables are allowed"
        )

    source_rows = validate_key(
        cursor, pair.source, pair.primary_key
    )

    target_rows = validate_key(
        cursor, pair.target, pair.primary_key
    )

    sql = build_reconciliation_sql(pair)
    cursor.execute(sql)

    results = {
        "INSERT": 0,
        "UPDATE": 0,
        "UNCHANGED": 0,
        "MISSING": 0,
    }

    for change_type, count in cursor.fetchall():
        if change_type not in results:
            raise ValueError(
                f"Unexpected change type: {change_type}"
            )

        results[change_type] = int(count)

    source_count = (
        results["INSERT"]
        + results["UPDATE"]
        + results["UNCHANGED"]
    )

    target_count = (
        results["UPDATE"]
        + results["UNCHANGED"]
        + results["MISSING"]
    )

    if source_count != source_rows:
        raise ValueError("Source row count mismatch")

    if target_count != target_rows:
        raise ValueError("Target row count mismatch")

    return {
        **results,
        "SOURCE_ROWS": source_rows,
        "TARGET_ROWS": target_rows,
    }
