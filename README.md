# Travel Analytics Platform

End-to-end data pipeline for a travel-industry CRM. Real-time events flow from a Pub/Sub simulator through a medallion architecture in BigQuery (Bronze → Silver → Gold), orchestrated by Airflow, transformed by dbt, and surfaced in a Streamlit KPI dashboard and an Apache Superset BI layer.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│               GCP · Travel Analytics Platform                        │
│                                                                     │
│   Simulator ──► Pub/Sub ──► Apache Beam ──► layer_bronze (BQ)      │
│   (publisher.py)                                  │                 │
│                                                   ▼                 │
│                                  dbt ──► layer_silver (BQ)         │
│                         (Airflow DAG)      │                        │
│                                            ▼                        │
│                                  dbt ──► layer_gold (BQ)           │
│                                            │                        │
│                              ┌─────────────┴──────────────┐        │
│                              ▼                             ▼        │
│                         Streamlit                     Superset      │
│                         (KPI + AI chat)           (Interactive BI)  │
└─────────────────────────────────────────────────────────────────────┘
```

## Stack

| Layer | Technology |
|-------|-----------|
| Event ingestion | Apache Beam (DirectRunner → Dataflow) |
| Message broker | Google Cloud Pub/Sub |
| Data warehouse | Google BigQuery (medallion: bronze / silver / gold) |
| Orchestration | Apache Airflow 3.x (LocalExecutor, Docker Compose) |
| Transformations | dbt + dbt-bigquery |
| KPI dashboard | Streamlit · Plotly (chart rendering for PDF export) |
| BI dashboard | Apache Superset |
| Infrastructure | Terraform (GCP resources) |
| Linting & safety | ruff, detect-secrets (pre-commit hooks) |

Architecture decisions are documented in [docs/adr/](docs/adr/).

---

## Repository Layout

```
.
├── airflow/              # Airflow Docker Compose + DAGs
│   └── dags/
├── dashboard/            # Streamlit app (app.py) + AI agent (agent.py)
├── dbt/                  # dbt project (dbt_health_monitor)
│   └── dbt_health_monitor/models/
│       ├── bronze/       # Sources pointing to layer_bronze
│       ├── silver/       # Cleaned / typed models
│       └── gold/         # Aggregated models consumed by dashboards
├── docs/adr/             # Architecture Decision Records
├── infra/data/           # Terraform — BigQuery, Pub/Sub, Service Account
├── ingestion/            # Apache Beam pipeline (beam_bronze.py)
├── scripts/              # VM bootstrap & deploy-key setup
├── simulator/            # CRM event publisher (publisher.py)
├── superset/             # Superset Docker Compose + setup scripts
└── tests/                # pytest unit tests
```

---

## Local Development

### Prerequisites

- Python 3.11+
- Docker + Docker Compose plugin
- A GCP project with BigQuery and Pub/Sub enabled, **or** `USE_MOCK=true` to use synthetic data

### 1. Clone and configure

```bash
git clone git@github.com:marcela-acosta/travel-analytics-platform.git
cd travel-analytics-platform
cp .env.example .env   # fill in GCP_PROJECT, GCP_DATASET, OPENAI_API_KEY, etc.
```

### 2. Install Python dependencies

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Install pre-commit hooks

```bash
pip install pre-commit
pre-commit install
```

Hooks run automatically on every commit: ruff (format + lint) and detect-secrets.

### 4. Run the Streamlit dashboard

```bash
# Mock data (no GCP credentials needed)
USE_MOCK=true streamlit run dashboard/app.py

# Live BigQuery data
USE_MOCK=false streamlit run dashboard/app.py
```

Dashboard available at **http://localhost:8501**

---

## Running the Full Stack

### Superset (BI dashboard)

```bash
cd superset
docker compose up -d

# First-time only: register BigQuery + create charts
docker exec superset-superset-1 python3 /app/superset/setup_bigquery.py
docker exec superset-superset-1 python3 /app/superset/create_dashboard.py
```

Dashboard available at **http://localhost:8088** · Login: `admin` / see `SUPERSET_ADMIN_PASSWORD` in `.env`

### Airflow (orchestration)

```bash
cd airflow
docker compose up -d
```

Web UI at **http://localhost:8080** · Default login: `airflow` / `airflow`

### Event simulator

```bash
# Publishes synthetic CRM events to Pub/Sub
python simulator/publisher.py
```

### Beam ingestion pipeline

```bash
# Reads from Pub/Sub and lands events in BigQuery layer_bronze
python ingestion/beam_bronze.py
```

### dbt transformations

```bash
cd dbt/dbt_health_monitor
dbt run          # bronze → silver → gold
dbt test         # run schema and custom tests
dbt docs generate --empty-catalog && dbt docs serve --port 8082
```

Lineage graph (including dashboard exposures) at **http://localhost:8082**

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_MOCK` | Use synthetic data instead of BigQuery | `true` |
| `GCP_PROJECT` | GCP project ID | `pipeline-health-mon-2026` |
| `GCP_DATASET` | BigQuery gold dataset | `layer_gold` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON | — |
| `OPENAI_API_KEY` | OpenAI key for the AI chat feature. Billed per token — typical usage costs < $0.01 per conversation with `gpt-4o-mini`. See [openai.com/pricing](https://openai.com/pricing). | — |
| `SUPERSET_ADMIN_PASSWORD` | Superset admin password | — |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | Email report delivery | — |

---

## Tests

```bash
pytest tests/ -v
```

---

## Infrastructure (Terraform)

```bash
cd infra/data
terraform init
terraform plan
terraform apply
```

Provisions: BigQuery datasets, Pub/Sub topic + subscription, and the pipeline service account with least-privilege IAM bindings.

---

## Deployment

The VM bootstrap script (`scripts/startup.sh`) runs once on first boot:
1. Installs Docker
2. Fetches the GitHub deploy key from Secret Manager
3. Clones this repository to `/opt/travel-analytics-platform`
4. Starts Airflow via Docker Compose

To set up the deploy key before the first `terraform apply`:

```bash
./scripts/setup-deploy-key.sh
```
