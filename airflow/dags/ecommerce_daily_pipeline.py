
"""
E-commerce Data Platform
BigQuery -> Snowflake STG -> RAW -> dbt

Airflow 3.3.1
Daily schedule: 06:00 Asia/Shanghai

RAW publishing requires explicit authorization.
dbt runs only after RAW publishing succeeds.
"""

import os
import subprocess
import sys

from datetime import timedelta
from pathlib import Path

import pendulum

from airflow.sdk import dag, task


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path("/opt/airflow/project")
INGESTION_DIR = PROJECT_ROOT / "ingestion"
DBT_PROJECT_DIR = PROJECT_ROOT / "ecomerce_dbt"
DBT_PROFILES_DIR = Path("/opt/airflow/dbt_config")

TIMEZONE = "Asia/Shanghai"


# ============================================================
# Command Runner
# ============================================================

def run_command(command, cwd=None, extra_env=None):

    env = os.environ.copy()

    env["PYTHONPATH"] = str(PROJECT_ROOT)
    env["PYTHONUNBUFFERED"] = "1"

    if extra_env:
        env.update(extra_env)

    print(
        "Running:",
        " ".join(map(str, command)),
        flush=True,
    )

    subprocess.run(
        [str(arg) for arg in command],
        cwd=str(cwd or PROJECT_ROOT),
        env=env,
        check=True,
    )


def run_ingestion(module, *args):

    if not INGESTION_DIR.is_dir():
        raise RuntimeError(
            f"Ingestion directory not found: {INGESTION_DIR}"
        )

    run_command([
        sys.executable,
        "-m",
        module,
        *args,
    ])


def run_dbt(*args):

    if not DBT_PROJECT_DIR.is_dir():
        raise RuntimeError("dbt project directory not found")

    if not (DBT_PROFILES_DIR / "profiles.yml").is_file():
        raise RuntimeError("dbt profiles.yml not found")

    target = os.getenv("DBT_RUN_TARGET", "dev").lower()

    if target not in {"dev", "prod"}:
        raise ValueError(f"Invalid dbt target: {target}")

    run_command(
        [
            "dbt",
            *args,
            "--target",
            target,
            "--project-dir",
            DBT_PROJECT_DIR,
            "--profiles-dir",
            DBT_PROFILES_DIR,
        ],
        extra_env={
            "DBT_LOG_PATH": "/opt/airflow/logs/dbt",
            "DBT_TARGET_PATH": "/opt/airflow/logs/dbt_target",
        },
    )


# ============================================================
# DAG
# ============================================================

@dag(
    dag_id="ecommerce_daily_pipeline",
    description="Daily BigQuery Snowflake dbt pipeline",

    start_date=pendulum.datetime(
        2026, 11, 5, tz=TIMEZONE
    ),

    schedule="0 6 * * *",
    catchup=False,

    max_active_runs=1,
    max_active_tasks=1,

    is_paused_upon_creation=True,

    tags=[
        "ecommerce",
        "bigquery",
        "snowflake",
        "dbt",
    ],
)
def ecommerce_daily_pipeline():

    # 1. BigQuery extraction
    @task(
        retries=0,
        execution_timeout=timedelta(hours=2),
    )
    def extract_bigquery():

        print("STEP 1: Extract BigQuery")

        run_ingestion(
            "ingestion.extract_all_tables"
        )

    # 2. Load staging
    @task(
        retries=0,
        execution_timeout=timedelta(hours=2),
    )
    def load_staging():

        print("STEP 2: Load Snowflake STG")

        run_command(
            [
                sys.executable,
                str(INGESTION_DIR / "load_all_tables.py"),
            ],
            cwd=INGESTION_DIR,
        )

    # 3. Validate snapshot
    @task(
        retries=0,
        execution_timeout=timedelta(hours=1),
    )
    def validate_snapshot():

        print("STEP 3: Validate Snapshot")

        run_ingestion(
            "ingestion.snapshot_refresh"
        )

    # 4. Publish RAW
    @task(
        retries=0,
        execution_timeout=timedelta(hours=2),
    )
    def publish_raw():

        print("STEP 4: Publish RAW")

        enabled = (
            os.getenv("ENABLE_RAW_REFRESH", "false")
            .strip().lower() == "true"
        )

        if not enabled:
            raise RuntimeError(
                "RAW publishing is not authorized. "
                "ENABLE_RAW_REFRESH must be true."
            )

        run_ingestion(
            "ingestion.snapshot_refresh",
            "--apply",
            "--confirm-rebaseline",
        )

        print("RAW publishing completed successfully")

    # 5. dbt build
    @task(
        retries=0,
        execution_timeout=timedelta(hours=2),
    )
    def build_dbt_models():

        print("STEP 5: dbt Build")

        run_dbt("build")

        print("dbt Build completed successfully")

    # Dependencies
    extract = extract_bigquery()
    staging = load_staging()
    validate = validate_snapshot()
    publish = publish_raw()
    dbt_build = build_dbt_models()

    extract >> staging >> validate >> publish >> dbt_build


ecommerce_daily_pipeline()
