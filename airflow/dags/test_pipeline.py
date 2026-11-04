
import pendulum
from airflow.sdk import dag, task


@dag(
    dag_id="ecommerce_test_pipeline",
    description="First Airflow pipeline for the E-commerce Data Platform",
    start_date=pendulum.datetime(2026, 11, 1, tz="Asia/Shanghai"),
    schedule=None,
    catchup=False,
    tags=["ecommerce", "learning"],
)
def ecommerce_test_pipeline():

    @task
    def extract():
        print("Step 1: Extract data")
        return 100

    @task
    def transform(record_count: int):
        print(f"Step 2: Transform {record_count} records")
        return record_count

    @task
    def load(record_count: int):
        print(f"Step 3: Load {record_count} records")
        print("Pipeline completed successfully!")

    extracted = extract()
    transformed = transform(extracted)
    load(transformed)


ecommerce_test_pipeline()
