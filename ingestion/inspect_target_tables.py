
import os
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

conn = snowflake.connector.connect(
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    user=os.environ["SNOWFLAKE_USER"],
    authenticator="PROGRAMMATIC_ACCESS_TOKEN",
    token=os.environ["SNOWFLAKE_TOKEN"],
    role="ECOM_LOADER",
    warehouse="ECOM_WH",
    database="ECOM_RAW",
    schema="THELOOK",
)

TABLES = ["USERS", "ORDERS", "ORDER_ITEMS", "PRODUCTS"]

try:
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE,
                   IS_NULLABLE, ORDINAL_POSITION
            FROM ECOM_RAW.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'THELOOK'
              AND TABLE_NAME IN (
                  'USERS', 'ORDERS', 'ORDER_ITEMS', 'PRODUCTS'
              )
            ORDER BY TABLE_NAME, ORDINAL_POSITION
        """)

        rows = cursor.fetchall()

    found_tables = set()

    for table_name, column_name, data_type, nullable, position in rows:
        if table_name not in found_tables:
            print(f"\n{'=' * 55}")
            print(f"Table: {table_name}")
            found_tables.add(table_name)

        print(
            f"{position:>2}. {column_name:<25} "
            f"{data_type:<20} nullable={nullable}"
        )

    print("\nMissing tables:")
    for table_name in TABLES:
        if table_name not in found_tables:
            print(f"- {table_name}")

finally:
    conn.close()
