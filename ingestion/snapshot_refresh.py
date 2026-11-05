
"""Atomic full-snapshot refresh for TheLook synthetic data.

Default is read-only. Explicit confirmation is required to
replace all four production RAW tables.
"""

import argparse
from ingestion.load_table import TABLE_CONFIG, get_connection
from ingestion.snapshot_publish import TABLES, table_names

# Minimum plausible staging counts for this project.
# These are safeguards, not proof of completeness.
MIN_ROWS = {
    "users": 90000,
    "products": 25000,
    "orders": 100000,
    "order_items": 150000,
}


def validate_table(cursor, name):
    source, target = table_names(name)
    key = TABLES[name]

    cursor.execute(f"""
        SELECT
            COUNT(*),
            COUNT(DISTINCT {key}),
            COUNT_IF({key} IS NULL)
        FROM {source}
    """)

    total, distinct_ids, null_ids = map(
        int, cursor.fetchone()
    )

    if total < MIN_ROWS[name]:
        raise RuntimeError(
            f"{name}: incomplete staging snapshot "
            f"({total} rows)"
        )

    if distinct_ids != total or null_ids != 0:
        raise RuntimeError(
            f"{name}: invalid primary keys"
        )

    return total


def validate_relationships(cursor):
    """Verify key relationships within the staging snapshot."""

    checks = {
        "orders_without_users": """
            SELECT COUNT(*)
            FROM ECOM_RAW.THELOOK.STG_ORDERS o
            LEFT JOIN ECOM_RAW.THELOOK.STG_USERS u
                ON o.USER_ID = u.ID
            WHERE u.ID IS NULL
        """,
        "items_without_orders": """
            SELECT COUNT(*)
            FROM ECOM_RAW.THELOOK.STG_ORDER_ITEMS i
            LEFT JOIN ECOM_RAW.THELOOK.STG_ORDERS o
                ON i.ORDER_ID = o.ORDER_ID
            WHERE o.ORDER_ID IS NULL
        """,
        "items_without_products": """
            SELECT COUNT(*)
            FROM ECOM_RAW.THELOOK.STG_ORDER_ITEMS i
            LEFT JOIN ECOM_RAW.THELOOK.STG_PRODUCTS p
                ON i.PRODUCT_ID = p.ID
            WHERE p.ID IS NULL
        """,
    }

    for label, sql in checks.items():
        cursor.execute(sql)
        count = int(cursor.fetchone()[0])

        print(f"{label}: {count}")

        if count != 0:
            raise RuntimeError(
                f"Relationship validation failed: {label}"
            )


def refresh(apply=False):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        try:
            expected = {}

            # Preflight: no writes.
            for name in TABLES:
                expected[name] = validate_table(cursor, name)
                print(
                    f"{name}: {expected[name]:,} source rows"
                )

            validate_relationships(cursor)

            if not apply:
                print("DRY RUN PASS: No RAW data changed.")
                return

            # No concurrent ingestion may modify STG
            # during this transaction.
            cursor.execute("BEGIN TRANSACTION")

            try:
                # DELETE is transactional, unlike TRUNCATE.
                for name in TABLES:
                    source, target = table_names(name)
                    columns = TABLE_CONFIG[name]["columns"]
                    column_list = ", ".join(columns)

                    cursor.execute(f"DELETE FROM {target}")

                    cursor.execute(f"""
                        INSERT INTO {target} ({column_list})
                        SELECT {column_list}
                        FROM {source}
                    """)

                    cursor.execute(
                        f"SELECT COUNT(*) FROM {target}"
                    )
                    actual = int(cursor.fetchone()[0])

                    if actual != expected[name]:
                        raise RuntimeError(
                            f"{name}: count mismatch "
                            f"{actual} != {expected[name]}"
                        )

                    print(
                        f"REFRESHED {name}: {actual:,} rows"
                    )

                validate_relationships(cursor)

                conn.commit()
                print("SUCCESS: Four RAW tables committed.")

            except Exception:
                conn.rollback()
                print("FAILED: Transaction rolled back.")
                raise

        finally:
            cursor.close()

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply", action="store_true"
    )
    parser.add_argument(
        "--confirm-rebaseline", action="store_true"
    )

    args = parser.parse_args()

    if args.apply and not args.confirm_rebaseline:
        parser.error(
            "--apply requires --confirm-rebaseline"
        )

    refresh(apply=args.apply)
