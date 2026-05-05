"""
Generate architecture diagrams for the Travel Analytics Platform presentation.

Run from the repo root:
    python docs/diagrams/generate.py

Requirements:
    pip install diagrams
    apt install graphviz   # or brew install graphviz on macOS
"""

import os

from diagrams import Diagram, Cluster, Edge
from diagrams.gcp.analytics import BigQuery, Pubsub, Dataflow
from diagrams.gcp.compute import Run
from diagrams.gcp.storage import GCS
from diagrams.gcp.devtools import Scheduler
from diagrams.onprem.workflow import Airflow
from diagrams.onprem.database import PostgreSQL
from diagrams.programming.language import Python

OUT = os.path.dirname(__file__)


# ── 1. System Architecture ────────────────────────────────────────────────────


def system_architecture():
    graph_attr = {
        "fontsize": "13",
        "bgcolor": "white",
        "pad": "0.5",
        "splines": "ortho",
    }
    with Diagram(
        "Travel Analytics Platform — System Architecture",
        filename=os.path.join(OUT, "system_architecture"),
        outformat="png",
        graph_attr=graph_attr,
        direction="LR",
        show=False,
    ):
        with Cluster("Data Sources"):
            simulator = Python("CRM Simulator\n(publisher.py)")

        with Cluster("GCP — us-central1"):
            pubsub = Pubsub("Pub/Sub\ncrm-events topic")

            with Cluster("GCE VM  e2-standard-8"):
                beam = Dataflow("Apache Beam\n(Direct Runner)")

                with Cluster("Docker — Airflow"):
                    airflow = Airflow("Airflow 3.2\n+ Cosmos")
                    pg_airflow = PostgreSQL("Airflow\nMetadata DB")
                    airflow >> pg_airflow

                with Cluster("Docker — Dashboards"):
                    streamlit = Python("Streamlit\nDashboard")
                    superset = Python("Apache\nSuperset 4.1")

            with Cluster("BigQuery  pipeline-health-mon-2026"):
                with Cluster("bronze"):
                    bq_bronze = BigQuery("crm_events (raw)")
                with Cluster("silver"):
                    bq_silver = BigQuery("slv_crm_events\n+ 25 models\n(incremental)")
                with Cluster("gold"):
                    bq_gold = BigQuery("5 gold views\n& tables")
                with Cluster("elementary"):
                    BigQuery("Data quality\nreports")

            gcs = GCS("GCS\ndbt artifacts")
            cloud_run = Run("Cloud Run\nvm-idle-checker")
            scheduler = Scheduler("Cloud Scheduler\nevery 30 min")

        simulator >> Edge(label="publish events") >> pubsub
        pubsub >> Edge(label="subscribe") >> beam
        beam >> Edge(label="write raw") >> bq_bronze
        bq_bronze >> Edge(label="dbt run\n(Cosmos DAG)") >> bq_silver
        bq_silver >> Edge(label="dbt run") >> bq_gold
        airflow >> Edge(label="orchestrate", style="dashed") >> bq_silver
        airflow >> Edge(label="", style="dashed") >> bq_gold
        airflow >> Edge(label="artifacts", style="dashed") >> gcs
        bq_gold >> Edge(label="query") >> streamlit
        bq_gold >> Edge(label="query") >> superset
        scheduler >> Edge(label="trigger") >> cloud_run
        cloud_run >> Edge(label="stop idle VM") >> beam

    print("✓ system_architecture.png")


# ── 2. Medallion Data Pipeline ────────────────────────────────────────────────


def data_pipeline():
    graph_attr = {
        "fontsize": "13",
        "bgcolor": "white",
        "pad": "0.6",
        "splines": "ortho",
        "nodesep": "0.8",
        "ranksep": "1.2",
    }
    with Diagram(
        "Travel Analytics Platform — Medallion Data Pipeline",
        filename=os.path.join(OUT, "data_pipeline"),
        outformat="png",
        graph_attr=graph_attr,
        direction="LR",
        show=False,
    ):
        simulator = Python(
            "CRM Simulator\npublisher.py\n\n15 agents · 5 products\n5 regions · ~1 msg/min"
        )
        pubsub = Pubsub("Pub/Sub\ncrm-events\n\n15 topics")
        beam = Python(
            "Apache Beam\nDirect Runner\nbeam_bronze.py\n\nparse · validate\nwrite to BQ"
        )

        with Cluster("BigQuery — Medallion Architecture"):
            with Cluster("🥉 BRONZE  (raw)"):
                bronze = BigQuery(
                    "bronze.crm_events\n\nschema: opportunity_id,\nstage, agent_id, product,\nregion, value,\nexpected_close_date,\nupdated_at, ingested_at"
                )

            with Cluster("🥈 SILVER  (cleaned · incremental)"):
                staging = BigQuery(
                    "staging.stg_*\n(ephemeral)\n\ntype casts, null checks"
                )
                silver = BigQuery(
                    "silver.slv_crm_events\n+ 25 event models\n\nincremental on ingested_at\nunique_key = row SK"
                )

            with Cluster("🥇 GOLD  (aggregated · views / tables)"):
                g1 = BigQuery(
                    "gld_dashboard_opportunities\n(view · date-computed\ndays_since_update, is_stale)"
                )
                g2 = BigQuery(
                    "gld_pipeline_by_stage\ngld_conversion_by_agent\ngld_conversion_by_product\n(tables · full refresh)"
                )
                g3 = BigQuery("gld_stale_opportunities\n(view · filters is_stale=true)")

        airflow = Airflow(
            "Airflow + Cosmos\ndbt_medallion_daily DAG\n\nsilver TaskGroup\ngold TaskGroup\nelementary"
        )
        streamlit = Python("Streamlit Dashboard\n\nfilters · AI agent\n(GPT-4o-mini)")
        superset = Python(
            "Apache Superset\nTravel Analytics Platform\n\n8 charts · 1 dashboard"
        )

        simulator >> Edge(label="publish") >> pubsub
        pubsub >> Edge(label="subscribe & parse") >> beam
        beam >> Edge(label="append row") >> bronze
        bronze >> Edge(label="stg_* views") >> staging
        staging >> Edge(label="incremental merge") >> silver
        silver >> Edge(label="aggregate") >> g1
        silver >> Edge(label="aggregate") >> g2
        silver >> Edge(label="filter stale") >> g3

        airflow >> Edge(label="daily schedule", style="dashed") >> silver
        airflow >> Edge(style="dashed") >> g1
        airflow >> Edge(style="dashed") >> g2

        g1 >> Edge(label="query") >> streamlit
        g1 >> Edge(label="query") >> superset
        g2 >> Edge(label="query") >> streamlit
        g2 >> Edge(label="query") >> superset
        g3 >> Edge(label="query") >> streamlit
        g3 >> Edge(label="query") >> superset

    print("✓ data_pipeline.png")


# ── 3. dbt Model Lineage ──────────────────────────────────────────────────────


def dbt_lineage():
    graph_attr = {
        "fontsize": "12",
        "bgcolor": "white",
        "pad": "0.5",
        "splines": "polyline",
        "nodesep": "0.4",
        "ranksep": "0.9",
    }
    with Diagram(
        "Travel Analytics Platform — dbt Model Lineage",
        filename=os.path.join(OUT, "dbt_lineage"),
        outformat="png",
        graph_attr=graph_attr,
        direction="LR",
        show=False,
    ):
        with Cluster("Bronze (source)"):
            src = BigQuery("bronze.crm_events")

        with Cluster("Staging (ephemeral)"):
            stg = BigQuery("stg_crm_events\n+ 14 stg_* models")

        with Cluster("Silver (incremental)"):
            slv_crm = BigQuery("slv_crm_events")
            slv_others = BigQuery(
                "slv_agency_events\nslv_booking_events\nslv_customer_events\n+ 22 more"
            )

        with Cluster("Gold"):
            with Cluster("Views (date-computed)"):
                gld_opps = BigQuery(
                    "gld_dashboard_opportunities\n(current_date fields)"
                )
                gld_stale = BigQuery("gld_stale_opportunities\n(is_stale filter)")

            with Cluster("Tables (full refresh)"):
                gld_stage = BigQuery("gld_pipeline_by_stage")
                gld_agent = BigQuery("gld_conversion_by_agent")
                gld_product = BigQuery("gld_conversion_by_product")

        src >> stg
        stg >> slv_crm
        stg >> slv_others

        slv_crm >> gld_opps
        gld_opps >> gld_stale
        gld_opps >> gld_stage
        gld_opps >> gld_agent
        gld_opps >> gld_product

    print("✓ dbt_lineage.png")


if __name__ == "__main__":
    system_architecture()
    data_pipeline()
    dbt_lineage()
    print("\nAll diagrams generated in docs/diagrams/")
