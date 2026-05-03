# ADR-0002 — Apache Airflow for Pipeline Orchestration

**Date:** 2026-01-15
**Status:** Accepted

## Context

The platform requires a scheduler that can coordinate multi-step pipelines: trigger dbt runs after Beam ingestion completes, run data quality checks, and send alerts on failure. The orchestrator must support DAG-based dependency management, be self-hostable on a single GCP VM (cost constraint), and have a mature GCP ecosystem (BigQuery operators, Pub/Sub sensors).

## Decision

Use **Apache Airflow 3.x** (LocalExecutor mode), self-hosted inside Docker Compose on the project VM alongside the other services.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Apache Airflow** | Industry standard, rich operator library, GCP providers built-in, large community | Heavy resource usage; UI can be slow on small VMs |
| **Prefect** | Modern Python-native API, easier local dev | Paid cloud tier required for full observability; smaller operator ecosystem |
| **Dagster** | Strong asset-centric model, great type system | Steeper learning curve; less GCP-native tooling |
| **Cloud Composer** | Managed Airflow on GCP | ~$400/month minimum — prohibitive for a student project |
| **Cron + shell scripts** | Zero overhead | No dependency management, no retries, no observability |

## Rationale

Airflow was chosen because it is the de facto standard in data engineering and covers every requirement: DAG-based dependency chains, built-in retries, BigQuery and dbt operators, and a web UI for monitoring. The LocalExecutor configuration runs all tasks in the same process, which is acceptable given the low task concurrency of this project and keeps memory usage manageable on the 4-vCPU VM. Cloud Composer was explicitly ruled out on cost grounds.

## Consequences

- **Positive:** Industry-recognized tooling; `BashOperator` + `dbt run` covers the full dbt orchestration need; Airflow logs are accessible in the Docker Compose stack without additional tooling.
- **Negative:** Airflow adds ~1 GB RAM overhead to the VM. LocalExecutor does not parallelize tasks across workers — acceptable now, but a migration to CeleryExecutor would be required for production-scale parallelism.
