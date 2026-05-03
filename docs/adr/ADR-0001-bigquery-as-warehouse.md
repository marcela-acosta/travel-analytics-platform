# ADR-0001 — BigQuery as Cloud Data Warehouse

**Date:** 2026-01-15
**Status:** Accepted

## Context

The platform needs a storage layer that can hold raw events from a Pub/Sub stream, staged CRM records, and the gold-layer aggregates that power the dashboard. The warehouse must handle semi-structured JSON payloads, scale without manual cluster management, and integrate natively with the rest of the GCP ecosystem already chosen for the project (Pub/Sub, Cloud Run, Secret Manager).

## Decision

Use **Google BigQuery** as the single data warehouse, organized in three datasets that mirror the medallion architecture:

| Dataset | Role |
|---------|------|
| `layer_bronze` | Raw events landed from Pub/Sub via Dataflow/Beam |
| `layer_silver` | Cleaned, deduplicated, typed records |
| `layer_gold` | Aggregated models consumed by dashboards |

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **BigQuery** | Serverless, native GCP integration, cheap on-demand pricing, JSON support, built-in partitioning | Vendor lock-in to GCP |
| **Snowflake** | Multi-cloud, mature ecosystem | Additional cost layer on top of GCP, separate auth to manage |
| **Amazon Redshift** | Mature, large community | Tied to AWS; conflicts with GCP-first infrastructure |
| **PostgreSQL (Cloud SQL)** | Familiar SQL, free tier | Not designed for analytical workloads; no built-in column storage |

## Rationale

BigQuery was the natural fit because the project already runs on GCP (Pub/Sub for ingestion, Secret Manager for credentials, Compute Engine for the VM). Its serverless model eliminates cluster management overhead, and the free tier (1 TB queries/month) is sufficient for the expected data volumes. Native support for nested/repeated fields simplifies landing raw JSON events without a schema-on-write constraint.

## Consequences

- **Positive:** Zero infrastructure management; cost scales with usage; native IAM integration; dbt-bigquery adapter is first-class.
- **Negative:** Queries billed per byte scanned — partitioning and clustering on gold tables is required to avoid runaway costs in production. Service account permissions must be carefully scoped (e.g., `bigquery.readsessions.create` intentionally withheld from the dashboard SA).
