
import csv
import os
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv
import uuid


# --------------------------------------------------
# 1. 项目配置
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data" / "raw"

DATABASE = "ECOM_RAW"
SCHEMA = "THELOOK"
WAREHOUSE = "ECOM_WH"
ROLE = "ECOM_LOADER"

STAGE = "ECOM_RAW.THELOOK.ECOM_LOAD_STAGE"

# CSV 表头与目标表字段的对应关系

TABLE_CONFIG = {
    "users": {
        "columns": [
            "ID",
            "FIRST_NAME",
            "LAST_NAME",
            "EMAIL",
            "AGE",
            "GENDER",
            "STATE",
            "STREET_ADDRESS",
            "POSTAL_CODE",
            "CITY",
            "COUNTRY",
            "LATITUDE",
            "LONGITUDE",
            "TRAFFIC_SOURCE",
            "CREATED_AT",
            "USER_GEOM",
        ]
    },

    "orders": {
        "columns": [
            "ORDER_ID",
            "USER_ID",
            "STATUS",
            "GENDER",
            "CREATED_AT",
            "RETURNED_AT",
            "SHIPPED_AT",
            "DELIVERED_AT",
            "NUM_OF_ITEM",
        ]
    },

    "order_items": {
        "columns": [
            "ID",
            "ORDER_ID",
            "USER_ID",
            "PRODUCT_ID",
            "INVENTORY_ITEM_ID",
            "STATUS",
            "CREATED_AT",
            "SHIPPED_AT",
            "DELIVERED_AT",
            "RETURNED_AT",
            "SALE_PRICE",
        ]
    },

    "products": {
        "columns": [
            "ID",
            "COST",
            "CATEGORY",
            "NAME",
            "BRAND",
            "RETAIL_PRICE",
            "DEPARTMENT",
            "SKU",
            "DISTRIBUTION_CENTER_ID",
        ]
    },
}



# --------------------------------------------------
# 2. 建立 Snowflake 连接
# --------------------------------------------------

def get_connection():
    load_dotenv(PROJECT_DIR / ".env")

    required = [
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_TOKEN",
    ]

    missing = [
        key for key in required
        if not os.getenv(key)
    ]

    if missing:
        raise RuntimeError(
            f".env 缺少配置项：{', '.join(missing)}"
        )

    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        authenticator="PROGRAMMATIC_ACCESS_TOKEN",
        token=os.environ["SNOWFLAKE_TOKEN"],
        role=ROLE,
        warehouse=WAREHOUSE,
        database=DATABASE,
        schema=SCHEMA,
    )


# --------------------------------------------------
# 3. 检查 CSV
# --------------------------------------------------

def inspect_csv(csv_path, columns):
    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV 文件不存在：{csv_path}"
        )

    with csv_path.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.reader(file)
        header = next(reader, None)

        if header != columns:
            raise ValueError(
                f"CSV 表头与配置不匹配：{csv_path.name}\n"
                f"Expected: {columns}\n"
                f"Actual:   {header}"
            )

        row_count = sum(1 for _ in reader)

    if row_count == 0:
        raise ValueError(
            f"CSV 没有数据行：{csv_path.name}"
        )

    return row_count


# --------------------------------------------------
# 4. 加载单张表
# --------------------------------------------------

def load_table(table_name):
    if table_name not in TABLE_CONFIG:
        raise ValueError(f"尚未配置此表：{table_name}")

    config = TABLE_CONFIG[table_name]
    columns = config["columns"]

    csv_path = DATA_DIR / f"{table_name}.csv"
    target_table = (
        f"{DATABASE}.{SCHEMA}.{table_name.upper()}"
    )
    staging_table = (
        f"{DATABASE}.{SCHEMA}.STG_{table_name.upper()}"
    )

    # 本次运行专用的临时表名，避免不同运行互相冲突
    run_id = uuid.uuid4().hex[:8].upper()
    run_table = (
        f"{DATABASE}.{SCHEMA}."
        f"STG_{table_name.upper()}_RUN_{run_id}"
    )

    csv_rows = inspect_csv(csv_path, columns)

    print(f"Table: {table_name}")
    print(f"CSV rows: {csv_rows:,}")
    print(f"Run table: {run_table}")

    conn = get_connection()
    run_table_created = False

    try:
        with conn.cursor() as cursor:
            # 1. 确保长期使用的暂存表存在
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS "
                f"{staging_table} LIKE {target_table}"
            )

            # 2. 上传 CSV 到 Stage
            stage_location = f"@{STAGE}/{table_name}"
            local_uri = (
                "file://" + csv_path.resolve().as_posix()
            )

            cursor.execute(
                f"PUT '{local_uri}' {stage_location} "
                "AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
            )

            put_results = cursor.fetchall()

            if not put_results:
                raise RuntimeError(
                    f"PUT 没有返回结果：{table_name}"
                )

            for result in put_results:
                print(f"Upload result: {result}")

            # 3. 创建本次运行专用的临时表
            cursor.execute(
                f"CREATE TEMPORARY TABLE {run_table} "
                f"LIKE {target_table}"
            )
            run_table_created = True

            # 4. 从 Stage 加载到临时表
            column_sql = ", ".join(columns)

            copy_sql = f"""
                COPY INTO {run_table} ({column_sql})
                FROM {stage_location}
                FILE_FORMAT = (
                    TYPE = CSV
                    SKIP_HEADER = 1
                    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
                    EMPTY_FIELD_AS_NULL = TRUE
                    SKIP_BYTE_ORDER_MARK = TRUE
                )
                PATTERN = '.*{table_name}[.]csv[.]gz'
                FORCE = TRUE
                ON_ERROR = 'ABORT_STATEMENT'
            """

            cursor.execute(copy_sql)
            copy_results = cursor.fetchall()

            for result in copy_results:
                print(f"COPY result: {result}")

            # 5. 校验临时表行数
            cursor.execute(
                f"SELECT COUNT(*) FROM {run_table}"
            )
            loaded_rows = cursor.fetchone()[0]

            if loaded_rows != csv_rows:
                raise RuntimeError(
                    f"行数不匹配：CSV={csv_rows:,}, "
                    f"Snowflake={loaded_rows:,}"
                )

            # 6. 校验主键唯一性和空值
            if table_name == "users":
                cursor.execute(f"""
                    SELECT
                        COUNT_IF(ID IS NULL),
                        COUNT(DISTINCT ID)
                    FROM {run_table}
                """)

                null_ids, distinct_ids = cursor.fetchone()

                if null_ids != 0 or distinct_ids != loaded_rows:
                    raise RuntimeError(
                        "主键校验失败："
                        f"NULL IDs={null_ids}, "
                        f"Distinct IDs={distinct_ids}, "
                        f"Rows={loaded_rows}"
                    )

            print(
                f"Validation passed: {table_name}, "
                f"{loaded_rows:,} rows"
            )

            # 7. 只有所有校验通过后，才替换暂存表数据
            # DDL 已在事务外执行；这里仅执行 DML
            cursor.execute("BEGIN")

            try:
                cursor.execute(
                    f"DELETE FROM {staging_table}"
                )

                cursor.execute(f"""
                    INSERT INTO {staging_table} ({column_sql})
                    SELECT {column_sql}
                    FROM {run_table}
                """)

                # 在提交前再次检查目标暂存表行数
                cursor.execute(
                    f"SELECT COUNT(*) FROM {staging_table}"
                )
                final_rows = cursor.fetchone()[0]

                if final_rows != loaded_rows:
                    raise RuntimeError(
                        f"替换后行数不匹配："
                        f"Expected={loaded_rows:,}, "
                        f"Actual={final_rows:,}"
                    )

                conn.commit()

            except Exception:
                conn.rollback()
                raise

            print(
                f"Load successful: {table_name}, "
                f"{final_rows:,} rows"
            )

            return final_rows

    finally:
        # 无论成功还是失败，都尝试清理本次运行的临时表
        try:
            if run_table_created:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"DROP TABLE IF EXISTS {run_table}"
                    )
        except Exception as cleanup_error:
            print(
                f"Warning: 临时表清理失败：{cleanup_error}"
            )
        finally:
            conn.close()


if __name__ == "__main__":
    load_table("order_items")