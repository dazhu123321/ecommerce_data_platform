
import csv
import os
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv


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
        ],
        "expected_rows": 100_000,
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
        raise ValueError(
            f"尚未配置此表：{table_name}"
        )

    config = TABLE_CONFIG[table_name]
    columns = config["columns"]

    csv_path = DATA_DIR / f"{table_name}.csv"
    staging_table = (
        f"{DATABASE}.{SCHEMA}.STG_{table_name.upper()}"
    )

    # 先验证文件，避免不必要的数据库操作
    csv_rows = inspect_csv(csv_path, columns)

    print(f"Table: {table_name}")
    print(f"CSV rows: {csv_rows:,}")

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            # 上传到命名 Stage 的独立子目录
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
                print(
                    f"Upload status: {result[6]}"
                    if len(result) > 6
                    else "Upload command completed."
                )

            # 暂存表不存在时，使用正式表结构创建
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS "
                f"{staging_table} "
                f"LIKE {DATABASE}.{SCHEMA}."
                f"{table_name.upper()}"
            )

            # 只清空暂存表，不触碰正式表
            cursor.execute(
                f"TRUNCATE TABLE {staging_table}"
            )

            column_sql = ", ".join(columns)

            # 通过 COPY INTO 批量加载
            copy_sql = f"""
                COPY INTO {staging_table} ({column_sql})
                FROM {stage_location}
                FILE_FORMAT = (
                    TYPE = CSV
                    SKIP_HEADER = 1
                    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
                    EMPTY_FIELD_AS_NULL = TRUE
                    SKIP_BYTE_ORDER_MARK = TRUE
                )
                PATTERN = '.*{table_name}\\.csv\\.gz'
                FORCE = TRUE
                ON_ERROR = 'ABORT_STATEMENT'
            """

            cursor.execute(copy_sql)
            copy_results = cursor.fetchall()

            for result in copy_results:
                print(f"COPY result: {result}")

            # 校验加载后的实际行数
            cursor.execute(
                f"SELECT COUNT(*) FROM {staging_table}"
            )
            loaded_rows = cursor.fetchone()[0]

            if loaded_rows != csv_rows:
                raise RuntimeError(
                    f"行数不匹配：CSV={csv_rows:,}, "
                    f"Snowflake={loaded_rows:,}"
                )

            print(
                f"Load successful: {table_name}, "
                f"{loaded_rows:,} rows"
            )

            return loaded_rows

    finally:
        conn.close()


if __name__ == "__main__":
    load_table("users")
