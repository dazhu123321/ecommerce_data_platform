
"""Publish four Snowflake staging snapshots using safe MERGE."""

import argparse
from ingestion.load_table import TABLE_CONFIG, get_connection

DATABASE = "ECOM_RAW"
SCHEMA = "THELOOK"

TABLES = {
    "users": "ID",
    "products": "ID",
    "orders": "ORDER_ID",
    "order_items": "ID",
}

# Protect against unexpectedly incomplete snapshots.
MAX_MISSING_RATE = 0.05


def table_names(name):
    if name not in TABLES:
        raise ValueError(f"Unsupported table: {name}")

    prefix = f"{DATABASE}.{SCHEMA}"
    return (
        f"{prefix}.STG_{name.upper()}",
        f"{prefix}.{name.upper()}",
    )


def validate_keys(cursor, table, key):
    cursor.execute(f"""
        SELECT
            COUNT(*),
            COUNT(DISTINCT {key}),
            COUNT_IF({key} IS NULL)
        FROM {table}
    """)

    total, unique, nulls = cursor.fetchone()
    total, unique, nulls = map(int, (total, unique, nulls))

    if total == 0:
        raise RuntimeError(f"Empty table: {table}")

    if unique != total or nulls != 0:
        raise RuntimeError(f"Invalid primary keys: {table}")

    return total


def changed_condition(columns, key):
    return "\n OR ".join(
        f"s.{col} IS DISTINCT FROM t.{col}"
        for col in columns
        if col != key
    )


def reconcile(cursor, name):
    source, target = table_names(name)
    key = TABLES[name]
    columns = TABLE_CONFIG[name]["columns"]

    source_rows = validate_keys(cursor, source, key)
    target_rows = validate_keys(cursor, target, key)

    sql = f"""
        SELECT
            CASE
                WHEN t.{key} IS NULL THEN 'INSERT'
                WHEN s.{key} IS NULL THEN 'MISSING'
                WHEN {changed_condition(columns, key)}
                    THEN 'UPDATE'
                ELSE 'UNCHANGED'
            END AS CHANGE_TYPE,
            COUNT(*) AS ROW_COUNT
        FROM {source} s
        FULL OUTER JOIN {target} t
            ON s.{key} = t.{key}
        GROUP BY 1
    """

    cursor.execute(sql)

    counts = {
        "INSERT": 0,
        "UPDATE": 0,
        "UNCHANGED": 0,
        "MISSING": 0,
    }

    for change_type, count in cursor.fetchall():
        if change_type not in counts:
            raise RuntimeError(f"Unknown category: {change_type}")
        counts[change_type] = int(count)

    if (
        counts["INSERT"]
        + counts["UPDATE"]
        + counts["UNCHANGED"]
        != source_rows
    ):
        raise RuntimeError(f"Source count mismatch: {name}")

    if (
        counts["UPDATE"]
        + counts["UNCHANGED"]
        + counts["MISSING"]
        != target_rows
    ):
        raise RuntimeError(f"Target count mismatch: {name}")

    return counts, source_rows, target_rows


def build_merge_sql(name):
    source, target = table_names(name)
    key = TABLES[name]
    columns = TABLE_CONFIG[name]["columns"]

    comparisons = changed_condition(columns, key)

    assignments = ",\n".join(
        f"t.{col} = s.{col}"
        for col in columns
        if col != key
    )

    insert_columns = ", ".join(columns)
    insert_values = ", ".join(
        f"s.{col}" for col in columns
    )

    return f"""
        MERGE INTO {target} t
        USING {source} s
            ON t.{key} = s.{key}

        WHEN MATCHED AND ({comparisons})
        THEN UPDATE SET
            {assignments}

        WHEN NOT MATCHED
        THEN INSERT ({insert_columns})
        VALUES ({insert_values})
    """


def publish(apply=False):
    conn = get_connection()
    conn.autocommit(False)

    try:
        with conn.cursor() as cursor:
            # Validate all four snapshots before writing.
            before = {}

            for name in TABLES:
                counts, source_rows, target_rows = reconcile(
                    cursor, name
                )

                before[name] = counts

                print(
                    f"{name}: source={source_rows:,}, "
                    f"target={target_rows:,}, {counts}"
                )

                missing_rate = (
                    counts["MISSING"] / target_rows
                )

                if missing_rate > MAX_MISSING_RATE:
                    raise RuntimeError(
                        f"{name}: missing rate "
                        f"{missing_rate:.2%} exceeds "
                        f"{MAX_MISSING_RATE:.0%}"
                    )

            if not apply:
                print("\nDRY RUN: No RAW tables modified.")
                return before

            # A single transaction for all four RAW tables.
            try:
                cursor.execute("BEGIN TRANSACTION")

                for name in TABLES:
                    cursor.execute(build_merge_sql(name))
                    merge_result = cursor.fetchone()

                    after, _, _ = reconcile(cursor, name)

                    if after["INSERT"] != 0:
                        raise RuntimeError(
                            f"{name}: inserts remain after MERGE"
                        )

                    if after["UPDATE"] != 0:
                        raise RuntimeError(
                            f"{name}: updates remain after MERGE"
                        )

                    if (
                        after["MISSING"]
                        != before[name]["MISSING"]
                    ):
                        raise RuntimeError(
                            f"{name}: missing count changed"
                        )

                    print(
                        f"MERGED {name}: "
                        f"{merge_result}, after={after}"
                    )

                conn.commit()
                print("\nSUCCESS: Four tables committed.")

            except Exception:
                conn.rollback()
                print("\nFAILED: Transaction rolled back.")
                raise

            return before

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write to production RAW tables",
    )

    parser.add_argument(
        "--confirm-production",
        action="store_true",
        help="Explicitly confirm production RAW writes",
    )

    args = parser.parse_args()

    if args.apply and not args.confirm_production:
        parser.error(
            "--apply requires --confirm-production"
        )

    publish(apply=args.apply)


if __name__ == "__main__":
    main()
