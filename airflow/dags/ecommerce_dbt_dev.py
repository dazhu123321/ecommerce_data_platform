
"""Manual dbt development validation DAG."""

import os
import subprocess

import pendulum
from airflow.sdk import dag, task


PROJECT_DIR = "/opt/airflow/project/ecomerce_dbt"
PROFILES_DIR = "/opt/airflow/dbt_config"


def execute_dbt(*arguments):
    env = os.environ.copy()

    # Keep dbt output outside the read-only project.
    env["DBT_LOG_PATH"] = "/opt/airflow/logs/dbt"
    env["DBT_TARGET_PATH"] = "/opt/airflow/logs/dbt_target"

    command = [
        "dbt",
        *arguments,
        "--project-dir",
        PROJECT_DIR,
        "--profiles-dir",
        PROFILES_DIR,
        "--target",
        "dev",
    ]

    print("Running:", " ".join(command), flush=True)

    subprocess.run(
        command,
        env=env,
        check=True,
    )


@dag(
    dag_id="ecommerce_dbt_dev",
    description="Manually validate dbt development models",
    start_date=pendulum.datetime(
        2026, 11, 5, tz="Asia/Shanghai"
    ),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=True,
    tags=["ecommerce", "dbt", "dev"],
)
def ecommerce_dbt_dev():

    @task(retries=0)
    def dbt_debug():
        execute_dbt("debug")

    @task(retries=0)
    def dbt_build():
        execute_dbt("build")

    debug = dbt_debug()
    build = dbt_build()

    debug >> build


ecommerce_dbt_dev()
