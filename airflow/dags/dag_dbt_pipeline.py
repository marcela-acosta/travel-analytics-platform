"""
Travel Analytics Platform — dbt orchestration DAG.

Runs every hour:
  dbt run (bronze) → dbt run (silver) → dbt run (gold) → dbt test (gold)

dbt project is mounted at /opt/airflow/dbt/dbt_health_monitor.
BigQuery auth is handled via GOOGLE_APPLICATION_CREDENTIALS (service account).
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

DBT_DIR = "/opt/airflow/dbt/dbt_health_monitor"
DBT_CMD = f"cd {DBT_DIR} && dbt"

default_args = {
    "owner": "data-engineering",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="dbt_pipeline",
    description="Bronze → Silver → Gold transformation + tests",
    start_date=datetime(2026, 1, 1),
    schedule="@hourly",
    catchup=False,
    default_args=default_args,
    tags=["dbt", "bigquery", "gold"],
) as dag:
    run_bronze = BashOperator(
        task_id="dbt_run_bronze",
        bash_command=f"{DBT_CMD} run --select bronze --profiles-dir . 2>&1",
    )

    run_silver = BashOperator(
        task_id="dbt_run_silver",
        bash_command=f"{DBT_CMD} run --select silver --profiles-dir . 2>&1",
    )

    run_gold = BashOperator(
        task_id="dbt_run_gold",
        bash_command=f"{DBT_CMD} run --select gold --profiles-dir . 2>&1",
    )

    test_gold = BashOperator(
        task_id="dbt_test_gold",
        bash_command=f"{DBT_CMD} test --select gold --profiles-dir . 2>&1",
    )

    run_bronze >> run_silver >> run_gold >> test_gold
