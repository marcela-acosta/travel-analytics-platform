"""
Travel Analytics Platform — dbt orchestration DAG using Astronomer Cosmos.

Cosmos converts each dbt model into an individual Airflow task, giving
fine-grained visibility, retries per model, and the full dbt lineage
graph rendered in the Airflow UI.

Pipeline:
  [DbtTaskGroup: bronze → silver → gold (one task per model)]
    → dbt run --select elementary  (Elementary observability tables)

Prerequisites:
  - Airflow connection "google_cloud_default" (Google Cloud Platform type)
    pointing to /opt/airflow/keys/pipeline-sa.json
    Set automatically via AIRFLOW_CONN_GOOGLE_CLOUD_DEFAULT in docker-compose.
  - dbt-bigquery and astronomer-cosmos installed (see airflow/Dockerfile).
  - Run `dbt deps` once inside the container to install dbt packages.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from cosmos import (
    DbtTaskGroup,
    ExecutionConfig,
    ProfileConfig,
    ProjectConfig,
    RenderConfig,
)
from cosmos.constants import LoadMode
from cosmos.profiles import GoogleCloudServiceAccountFileProfileMapping

GCP_CONN_ID = "google_cloud_default"
DBT_DIR = "/opt/airflow/dbt/dbt_health_monitor"
DBT_BIN = "/home/airflow/.local/bin/dbt"

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
    dag_id="dbt_pipeline",
    description="dbt bronze→silver→gold via Cosmos + Elementary observability",
    start_date=datetime(2026, 1, 1),
    schedule="@hourly",
    catchup=False,
    default_args=default_args,
    tags=["dbt", "cosmos", "bigquery"],
) as dag:
    transform = DbtTaskGroup(
        group_id="transform",
        project_config=ProjectConfig(dbt_project_path=DBT_DIR),
        profile_config=profile_config,
        execution_config=ExecutionConfig(dbt_executable_path=DBT_BIN),
        render_config=RenderConfig(load_method=LoadMode.DBT_LS),
    )

    run_elementary = BashOperator(
        task_id="dbt_run_elementary",
        bash_command=f"cd {DBT_DIR} && {DBT_BIN} run --select elementary --profiles-dir . 2>&1",
    )

    transform >> run_elementary
