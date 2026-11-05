
"""Read-only diagnosis of Snowflake snapshot differences."""

import argparse

from ingestion.load_table import TABLE_CONFIG, get_connection
from ingestion.snapshot_publish import TABLES, table_names


def diagnose(table_name):
    if table_name not in TABLES:
        raise ValueError(f"Unsupported table: {table_name}")

    source, target = table_names(table_name)
    key = TABLES[table_name]

    columns = [
        col for col in TABLE_CONFIG[table_name]["columns"]
        if col != key
    ]

    expressions = [
        (
            f"COUNT_IF("
            f"s.{col} IS DISTINCT FROM t.{col}"
            f") AS \"{col}\""
        )
        for col in columns
    ]

    sql = f"""
        SELECT
            COUNT(*) AS MATCHED_ROWS,
            {", ".join(expressions)}
        FROM {source} s
        INNER JOIN {target} t
            ON s.{key} = t.{key}
    """

    conn = get_connection()

    try:
        cursor = conn.cursor()

        try:
            cursor.execute(sql)
            values = cursor.fetchone()

            print(f"\nTABLE: {table_name.upper()}")
            print(f"MATCHED_ROWS: {values[0]:,}")
            print("-" * 48)

            for column, count in zip(columns, values[1:]):
                print(f"{column:<25} {int(count or 0):>10,}")

        finally:
            cursor.close()

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--table",
        choices=list(TABLES),
        required=True,
    )

    args = parser.parse_args()
    diagnose(args.table)


if __name__ == "__main__":
    main()
