
from load_table import TABLE_CONFIG, get_connection


DATABASE = "ECOM_RAW"
SCHEMA = "THELOOK"

# 删除旧数据时先处理子表，再处理父表
DELETE_ORDER = [
    "order_items",
    "orders",
    "products",
    "users",
]

# 插入新数据时先处理父表，再处理子表
INSERT_ORDER = [
    "users",
    "products",
    "orders",
    "order_items",
]


def publish_tables():
    conn = get_connection()

    try:
        # 禁止每条 DML 语句自动单独提交
        conn.autocommit(False)

        with conn.cursor() as cursor:
            cursor.execute("BEGIN")

            try:
                # 1. 清理正式表旧数据
                for table_name in DELETE_ORDER:
                    target_table = (
                        f"{DATABASE}.{SCHEMA}."
                        f"{table_name.upper()}"
                    )

                    cursor.execute(
                        f"DELETE FROM {target_table}"
                    )

                    print(
                        f"Cleared target: {target_table}"
                    )

                # 2. 从 STG 表写入正式表
                for table_name in INSERT_ORDER:
                    columns = TABLE_CONFIG[table_name][
                        "columns"
                    ]

                    column_sql = ", ".join(columns)

                    staging_table = (
                        f"{DATABASE}.{SCHEMA}."
                        f"STG_{table_name.upper()}"
                    )

                    target_table = (
                        f"{DATABASE}.{SCHEMA}."
                        f"{table_name.upper()}"
                    )

                    # 查询暂存表行数
                    cursor.execute(
                        f"SELECT COUNT(*) FROM "
                        f"{staging_table}"
                    )
                    staging_rows = cursor.fetchone()[0]

                    # 明确指定字段，避免依赖 SELECT *
                    cursor.execute(f"""
                        INSERT INTO {target_table}
                            ({column_sql})
                        SELECT {column_sql}
                        FROM {staging_table}
                    """)

                    # 验证正式表行数
                    cursor.execute(
                        f"SELECT COUNT(*) FROM "
                        f"{target_table}"
                    )
                    target_rows = cursor.fetchone()[0]

                    if target_rows != staging_rows:
                        raise RuntimeError(
                            f"{table_name} 行数不匹配："
                            f"STG={staging_rows:,}, "
                            f"Target={target_rows:,}"
                        )

                    print(
                        f"Published {table_name}: "
                        f"{target_rows:,} rows"
                    )

                # 3. 四张表全部成功后统一提交
                conn.commit()

                print("\nAll tables published successfully.")

            except Exception:
                # 任意一步失败，撤销本次事务中的数据修改
                conn.rollback()
                print(
                    "\nPublish failed. "
                    "Transaction rolled back."
                )
                raise

    finally:
        conn.close()


if __name__ == "__main__":
    publish_tables()
