
import csv
from pathlib import Path

from google.cloud import bigquery


# ==========================================
# 1. 项目配置
# ==========================================

PROJECT_ID = "hardy-palace-464004-c3"
SOURCE_DATASET = "bigquery-public-data.thelook_ecommerce"

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "data" / "raw"


# ==========================================
# 2. 定义四张源表的字段及顺序
#    与 Snowflake 目标表的字段名对应
# ==========================================

TABLES = {
    "users": [
        "id",
        "first_name",
        "last_name",
        "email",
        "age",
        "gender",
        "state",
        "street_address",
        "postal_code",
        "city",
        "country",
        "latitude",
        "longitude",
        "traffic_source",
        "created_at",
        "user_geom",
    ],
    "orders": [
        "order_id",
        "user_id",
        "status",
        "gender",
        "created_at",
        "returned_at",
        "shipped_at",
        "delivered_at",
        "num_of_item",
    ],
    "order_items": [
        "id",
        "order_id",
        "user_id",
        "product_id",
        "inventory_item_id",
        "status",
        "created_at",
        "shipped_at",
        "delivered_at",
        "returned_at",
        "sale_price",
    ],
    "products": [
        "id",
        "cost",
        "category",
        "name",
        "brand",
        "retail_price",
        "department",
        "sku",
        "distribution_center_id",
    ],
}


# ==========================================
# 3. 构建 SQL
#    将 GEOGRAPHY 转换为 WKT 字符串
# ==========================================

def build_query(table_name, columns):
    selected_columns = []

    for column in columns:
        if table_name == "users" and column == "user_geom":
            selected_columns.append(
                "ST_ASTEXT(user_geom) AS user_geom"
            )
        else:
            selected_columns.append(f"`{column}`")

    column_sql = ",\n    ".join(selected_columns)

    return f"""
        SELECT
            {column_sql}
        FROM `{SOURCE_DATASET}.{table_name}`
    """


# ==========================================
# 4. 提取单张表并写入 CSV
# ==========================================

def extract_table(client, table_name, columns):
    table_id = f"{SOURCE_DATASET}.{table_name}"
    output_file = OUTPUT_DIR / f"{table_name}.csv"

    print(f"\nExtracting: {table_id}")

    query = build_query(table_name, columns)

    # 执行查询；result() 逐页读取结果，不把整张表
    # 一次性转换成 Pandas DataFrame
    query_job = client.query(query)
    rows = query_job.result(page_size=10000)

    row_count = 0

    # newline="" 避免 CSV 出现多余空行
    with output_file.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)

        # CSV 表头统一大写，匹配 Snowflake 字段名
        writer.writerow([column.upper() for column in columns])

        for row in rows:
            values = []

            for column in columns:
                value = row[column]

                # 将日期、时间转换为标准 ISO 字符串
                if value is not None and hasattr(value, "isoformat"):
                    value = value.isoformat()

                values.append(value)

            # None 会被 CSV 写为留空字段
            writer.writerow(values)
            row_count += 1

    print(f"Rows exported: {row_count:,}")
    print(f"Output file: {output_file}")

    return row_count


# ==========================================
# 5. 执行四表提取
# ==========================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    client = bigquery.Client(project=PROJECT_ID)
    results = {}

    try:
        for table_name, columns in TABLES.items():
            results[table_name] = extract_table(
                client,
                table_name,
                columns,
            )
    finally:
        client.close()

    print("\n" + "=" * 50)
    print("EXTRACTION SUMMARY")
    print("=" * 50)

    for table_name, row_count in results.items():
        print(f"{table_name:<15} {row_count:>10,} rows")

    print("-" * 50)
    print(f"{'TOTAL':<15} {sum(results.values()):>10,} rows")
    print("\nAll four tables exported successfully.")


if __name__ == "__main__":
    main()
