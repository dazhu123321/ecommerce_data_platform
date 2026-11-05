
"""
E-commerce Data Platform
Daily BigQuery -> Snowflake -> dbt Pipeline

Airflow: 3.3.1

Flow:
    Extract BigQuery
        -> Load Snowflake STG
        -> Validate Snapshot
        -> Publish RAW
        -> dbt Build

Safety:
    - RAW publishing disabled by default
    - No automatic physical deletion through MERGE
    - Full snapshot rebaseline uses snapshot_refresh.py
    - dbt only runs after successful RAW publishing
    - Only one active DAG run at a time
"""

import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pendulum

from airflow.sdk import dag, task
from airflow.exceptions import AirflowSkipException


# ============================================================
# 1. Configuration
# ============================================================

PROJECT_ROOT = Path("/opt/airflow/project")

INGESTION_DIR = PROJECT_ROOT / "ingestion"

DBT_PROJECT_DIR = PROJECT_ROOT / "ecomerce_dbt"

DBT_PROFILES_DIR = Path("/opt/airflow/dbt_config")

TIMEZONE = "Asia/Shanghai"


# ============================================================
# 2. Common Command Runner
# ============================================================

def run_command(command, cwd=None, extra_env=None):
    """
    Execute a command inside the Airflow Worker.

    - Stream output to Airflow task logs
    - Fail task if subprocess exits with non-zero code
    """

    env = os.environ.copy()

    env["PYTHONPATH"] = str(PROJECT_ROOT)

    env["PYTHONUNBUFFERED"] = "1"

    if extra_env:
        env.update(extra_env)

    print("=" * 60, flush=True)
    print("COMMAND:", " ".join(map(str, command)), flush=True)
    print("=" * 60, flush=True)

    subprocess.run(
        [str(arg) for arg in command],
        cwd=str(cwd or PROJECT_ROOT),
        env=env,
        check=True,
    )

    print("COMMAND SUCCESS", flush=True)


def run_ingestion(module, *args):
    """Execute an ingestion Python module."""

    if not INGESTION_DIR.is_dir():
        raise RuntimeError(
            f"Missing ingestion directory: {INGESTION_DIR}"
        )

    run_command([
        sys.executable,
        "-m",
        module,
        *args,
    ])


def run_dbt(*args):
    """Execute dbt with explicit project and profile paths."""

    if not DBT_PROJECT_DIR.is_dir():
        raise RuntimeError(
            f"Missing dbt project: {DBT_PROJECT_DIR}"
        )

    if not (DBT_PROFILES_DIR / "profiles.yml").is_file():
        raise RuntimeError("Missing dbt profiles.yml")

    dbt_target = os.getenv("DBT_RUN_TARGET", "prod").lower()

    if dbt_target not in {"dev", "prod"}:
        raise ValueError("Invalid DBT_RUN_TARGET")

    run_command(
        [
            "dbt",
            *args,
            "--target",
            dbt_target,
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
# 3. DAG Definition
# ============================================================

@dag(
    dag_id="ecommerce_daily_pipeline",

    description=(
        "Daily BigQuery to Snowflake "
        "snapshot and dbt pipeline"
    ),

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
        "daily",
    ],
)
def ecommerce_daily_pipeline():

    # --------------------------------------------------------
    # Task 1 - Extract BigQuery
    # --------------------------------------------------------

    @task(
        retries=0,
        execution_timeout=timedelta(hours=2),
    )
    def extract_bigquery():

        print("STEP 1: Extracting BigQuery snapshots")

        run_ingestion(
            "ingestion.extract_all_tables"
        )

        print("BigQuery extraction completed")

    # --------------------------------------------------------
    # Task 2 - Load Snowflake STG
    # --------------------------------------------------------

    @task(
        retries=0,
        execution_timeout=timedelta(hours=2),
    )
    def load_staging():

        print("STEP 2: Loading Snowflake staging tables")

        # Existing script uses local imports from load_table.
        run_command(
            [
                sys.executable,
                str(INGESTION_DIR / "load_all_tables.py"),
            ],
            cwd=INGESTION_DIR,
        )

        print("Snowflake STG loading completed")

    # --------------------------------------------------------
    # Task 3 - Validate Snapshot
    # --------------------------------------------------------

    @task(
        retries=0,
        execution_timeout=timedelta(hours=1),
    )
    def validate_snapshot():

        print("STEP 3: Validating snapshots")

        # Default mode is read-only.
        run_ingestion(
            "ingestion.snapshot_refresh"
        )

        print("Snapshot validation passed")

    # --------------------------------------------------------
    # Task 4 - Publish RAW
    # --------------------------------------------------------

    @task(
        retries=0,
        execution_timeout=timedelta(hours=2),
    )
    def publish_raw():

        print("STEP 4: Publishing Snowflake RAW")

        enabled = (
            os.getenv(
                "ENABLE_RAW_REFRESH", "false"
            ).strip().lower() == "true"
        )

        if not enabled:
            raise AirflowSkipException(
                "RAW publishing disabled. "
                "Set ENABLE_RAW_REFRESH=true only "
                "after production safeguards are approved."
            )

        run_ingestion(
            "ingestion.snapshot_refresh",
            "--apply",
            "--confirm-rebaseline",
        )

        print("Snowflake RAW published successfully")

    # --------------------------------------------------------
    # Task 5 - dbt Build
    # --------------------------------------------------------

    @task(
        retries=1,
        retry_delay=timedelta(minutes=5),
        execution_timeout=timedelta(hours=2),
    )

    @task(
        retries=1,
        retry_delay=timedelta(minutes=5),
        execution_timeout=timedelta(hours=2),
    )
    def build_dbt_models():
        """Build dbt models after validation or RAW publishing."""

        context = get_current_context()
        ti = context["ti"]

        publish_state = ti.get_previous_ti()
        # Determine mode from the publishing flag.
        publish_enabled = (
            os.getenv("ENABLE_RAW_REFRESH", "false")
            .strip().lower() == "true"
        )

        if publish_enabled:
            target = "prod"
            print("RAW publishing enabled. Building dbt PROD.")
        else:
            target = "dev"
            print("RAW publishing skipped. Building dbt DEV.")

        run_command(
            [
                "dbt",
                "build",
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

        print(f"dbt {target} build completed successfully")


    # --------------------------------------------------------
    # Task Dependencies
    # --------------------------------------------------------

    extract = extract_bigquery()

    staging = load_staging()

    validate = validate_snapshot()

    publish = publish_raw()

    dbt_build = build_dbt_models()

    extract >> staging >> validate >> publish >> dbt_build


# Register DAG
ecommerce_daily_pipeline()
