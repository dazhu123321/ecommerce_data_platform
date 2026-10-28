
from google.cloud import bigquery

PROJECT_ID = "hardy-palace-464004-c3"
DATASET = "bigquery-public-data.thelook_ecommerce"

TABLES = [
    "users",
    "orders",
    "order_items",
    "products",
]


def main():
    client = bigquery.Client(project=PROJECT_ID)

    for table_name in TABLES:
        table_id = f"{DATASET}.{table_name}"
        table = client.get_table(table_id)

        print(f"\n{'=' * 60}")
        print(f"Table: {table_name}")
        print(f"Rows (metadata): {table.num_rows:,}")
        print(f"Columns: {len(table.schema)}")
        print("-" * 60)

        for field in table.schema:
            print(
                f"{field.name:<25} "
                f"{field.field_type:<12} "
                f"mode={field.mode}"
            )

    print("\nSource schema inspection completed.")


if __name__ == "__main__":
    main()
