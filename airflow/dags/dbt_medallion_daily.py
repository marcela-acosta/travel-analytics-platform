"""Daily Cosmos DAG for the dbt health monitor medallion layers."""

from datetime import datetime
from pathlib import Path

from cosmos import DbtDag, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import TestBehavior
from cosmos.profiles import GoogleCloudOauthProfileMapping

DBT_PROJECT_PATH = Path("/opt/airflow/dbt/dbt_health_monitor")

profile_config = ProfileConfig(
    profile_name="dbt_health_monitor",
    target_name="dev",
    profile_mapping=GoogleCloudOauthProfileMapping(
                 conn_id="google_cloud_default",
        profile_args={
            "project": "pipeline-health-mon-2026",
            "dataset": "layer",
            "location": "us-central1",
        },
    ),
)

dbt_medallion_daily = DbtDag(
    dag_id="dbt_medallion_daily",
    project_config=ProjectConfig(DBT_PROJECT_PATH, project_name="dbt_health_monitor"),
    profile_config=profile_config,
    render_config=RenderConfig(
        select=["path:models/silver", "path:models/gold"],
        group_nodes_by_folder=True,
        test_behavior=TestBehavior.AFTER_ALL,
        enable_mock_profile=False,
    ),
    operator_args={"install_deps": True},
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["dbt", "bigquery", "medallion"],
    default_args={"retries": 1},
)