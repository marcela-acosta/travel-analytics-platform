# ADR-0003 — dbt for Data Transformations

**Date:** 2026-01-15
**Status:** Accepted

## Context

Raw CRM events in `layer_bronze` need to be cleaned, typed, and aggregated into the gold models that power the dashboard KPIs. The transformation layer must be version-controlled, testable, and produce lineage documentation that shows which upstream tables feed each downstream dashboard. The team is SQL-proficient but has limited Spark/PySpark experience.

## Decision

Use **dbt (data build tool)** with the `dbt-bigquery` adapter to define all Silver and Gold layer transformations as SQL models. Expose downstream dashboards using dbt **exposures** so that `dbt docs` generates end-to-end lineage from raw events to dashboard.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **dbt** | SQL-native, version-controlled, built-in tests and docs, first-class BigQuery support, exposures for lineage | Python transformations require custom macros or `dbt-python` models |
| **Apache Spark (PySpark)** | Handles very large scale; Python-native | Cluster overhead; overkill for this data volume; no native lineage docs |
| **Plain SQL scripts** | Zero tooling overhead | No dependency management, no tests, no lineage, no documentation generation |
| **SQLMesh** | Modern dbt alternative with state-aware runs | Smaller community; less stable BigQuery adapter |

## Rationale

dbt maps directly to the team's SQL skills and imposes a structure (sources → staging → gold) that naturally enforces the medallion architecture. The `exposures.yml` feature satisfies the professor's lineage documentation requirement out of the box — running `dbt docs generate && dbt docs serve` produces an interactive DAG from Pub/Sub events all the way to the Streamlit and Superset dashboards. Built-in schema tests (`not_null`, `unique`, `accepted_values`) replace the need for a separate data quality framework at this stage.

## Consequences

- **Positive:** Full lineage graph visible in `dbt docs`; schema tests catch data quality issues before gold models run; SQL models are easy to review and audit.
- **Negative:** dbt does not orchestrate itself — Airflow (ADR-0002) is required to schedule `dbt run` and `dbt test`. Complex stateful transformations (e.g., sessionization of clickstream events) would require Python models or moving logic upstream into Beam.
