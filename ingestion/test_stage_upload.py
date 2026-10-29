
import os
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv


# 1. 加载项目根目录的 .env
PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

# 2. 定位本地 CSV
csv_path = PROJECT_DIR / "data" / "raw" / "users.csv"

if not csv_path.exists():
    raise FileNotFoundError(f"找不到文件：{csv_path}")

# 3. 连接 Snowflake
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
        # 4. 上传文件到命名内部 Stage
        stage_path = (
            "@ECOM_RAW.THELOOK.ECOM_LOAD_STAGE"
        )

        put_sql = (
            f"PUT 'file://{csv_path.as_posix()}' "
            f"{stage_path}/users "
            "AUTO_COMPRESS=TRUE "
            "OVERWRITE=TRUE"
        )

        cursor.execute(put_sql)

        for result in cursor.fetchall():
            # 输出上传状态，不输出任何认证信息
            print(result)

        # 5. 确认 Stage 中存在上传文件
        cursor.execute(
            "LIST @ECOM_RAW.THELOOK.ECOM_LOAD_STAGE/users"
        )

        files = cursor.fetchall()

        print("\nFiles found in stage:")
        for file_info in files:
            print(file_info[0], file_info[1])

        if not files:
            raise RuntimeError(
                "上传命令执行后，Stage 中没有找到文件"
            )

        print("\nStage upload test successful!")

finally:
    conn.close()
