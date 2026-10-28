
import os
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv

# 读取项目根目录下的 .env
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

try:
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT
                CURRENT_USER(),
                CURRENT_ROLE(),
                CURRENT_WAREHOUSE(),
                CURRENT_DATABASE(),
                CURRENT_SCHEMA()
        """)

        result = cursor.fetchone()

    print("Snowflake connection successful!")
    print("User:", result[0])
    print("Role:", result[1])
    print("Warehouse:", result[2])
    print("Database:", result[3])
    print("Schema:", result[4])

finally:
    conn.close()
