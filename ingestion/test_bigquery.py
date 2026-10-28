
from google.cloud import bigquery

PROJECT_ID = "hardy-palace-464004-c3"

client = bigquery.Client(project=PROJECT_ID)

query = """
SELECT
    id,
    name,
    category,
    retail_price
FROM `bigquery-public-data.thelook_ecommerce.products`
LIMIT 5
"""

results = client.query(query).result()

for row in results:
    print(dict(row))

print("BigQuery connection successful!")
