"""
Travel Analytics Platform — dbt orchestration DAG using Astronomer Cosmos.

Cosmos converts each dbt model into an individual Airflow task, giving
fine-grained visibility, retries per model, and the full dbt lineage
graph rendered in the Airflow UI grouped by layer (gold / silver).

Pipeline:
  models > silver > [one task per silver model]
  models > gold   > [one task per gold model]
    → dbt_run_elementary  (Elementary observability tables)

Staging tables (stg_*) are assumed to be already materialized in BigQuery
by the bronze pipeline. Only silver and gold run as individual Cosmos tasks.
Tests run after all models complete (TestBehavior.AFTER_ALL).

Prerequisites:
  - Airflow connection "google_cloud_default" set via
    AIRFLOW_CONN_GOOGLE_CLOUD_DEFAULT in docker-compose.
  - SA key at /opt/airflow/keys/pipeline-sa.json
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup
from cosmos import (
    DbtTaskGroup,
    ExecutionConfig,
    ProfileConfig,
    ProjectConfig,
    RenderConfig,
)
from cosmos.constants import LoadMode, TestBehavior
from cosmos.profiles import GoogleCloudServiceAccountFileProfileMapping

GCP_CONN_ID = "google_cloud_default"
DBT_DIR = "/opt/airflow/dbt/dbt_health_monitor"
DBT_BIN = "/home/airflow/.local/bin/dbt"
DBT_MANIFEST = f"{DBT_DIR}/target/manifest.json"

profile_config = ProfileConfig(
    profile_name="dbt_health_monitor",
    target_name="dev",
    profile_mapping=GoogleCloudServiceAccountFileProfileMapping(
        conn_id=GCP_CONN_ID,
        profile_args={
            "project": "pipeline-health-mon-2026",
            "dataset": "layer",
            "location": "us-central1",
            "threads": 4,
        },
    ),
)

default_args = {
    "owner": "data-engineering",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="dbt_medallion_daily",
    description="dbt silver→gold via Cosmos + Elementary observability",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    default_args=default_args,
    tags=["dbt", "cosmos", "bigquery"],
) as dag:
    with TaskGroup(group_id="models") as models:
        silver = DbtTaskGroup(
            group_id="silver",
            project_config=ProjectConfig(
                dbt_project_path=DBT_DIR,
                manifest_path=DBT_MANIFEST,
            ),
            profile_config=profile_config,
            execution_config=ExecutionConfig(dbt_executable_path=DBT_BIN),
            operator_args={"install_deps": True},
            render_config=RenderConfig(
                load_method=LoadMode.DBT_MANIFEST,
                select=["path:models/silver"],
                exclude=["package:elementary"],
                test_behavior=TestBehavior.AFTER_ALL,
            ),
        )

        gold = DbtTaskGroup(
            group_id="gold",
            project_config=ProjectConfig(
                dbt_project_path=DBT_DIR,
                manifest_path=DBT_MANIFEST,
            ),
            profile_config=profile_config,
            execution_config=ExecutionConfig(dbt_executable_path=DBT_BIN),
            operator_args={"install_deps": True},
            render_config=RenderConfig(
                load_method=LoadMode.DBT_MANIFEST,
                select=["path:models/gold"],
                exclude=["package:elementary"],
                test_behavior=TestBehavior.AFTER_ALL,
            ),
        )

    run_elementary = BashOperator(
        task_id="dbt_run_elementary",
        bash_command=(
            f"cd {DBT_DIR} && {DBT_BIN} run "
            "--select elementary "
            "--profiles-dir . "
            "--log-path /tmp/dbt_logs 2>&1"
        ),
    )

    models >> run_elementary
