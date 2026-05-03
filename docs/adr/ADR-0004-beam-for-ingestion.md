# ADR-0004 — Apache Beam for Event Ingestion

**Date:** 2026-01-15
**Status:** Accepted

## Context

CRM events are published to a Google Cloud Pub/Sub topic by a simulator that mimics real-time activity (bookings, stage changes, support tickets). These events must be consumed, validated, and landed in BigQuery's bronze layer with low latency. The ingestion layer must handle schema variation across event types and be runnable both locally (DirectRunner for development) and on GCP Dataflow (for production scale).

## Decision

Use **Apache Beam** (`beam_bronze.py`) with the **DirectRunner** for the current deployment. The pipeline reads from the `crm-events-sub` Pub/Sub subscription, parses JSON, adds metadata (ingestion timestamp, event type), and writes to `layer_bronze.crm_raw_events` in BigQuery.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Apache Beam + DirectRunner** | Runner-agnostic (same code runs on Dataflow); native Pub/Sub and BigQuery IOs; handles late data and windowing | More boilerplate than simpler alternatives |
| **Dataflow (managed Beam)** | Fully managed, auto-scales | ~$0.10/vCPU-hour — unnecessary cost for current data volumes |
| **Cloud Functions / Cloud Run** | Simple, event-driven, zero infra | No built-in windowing or exactly-once guarantees; harder to batch writes efficiently |
| **Kafka + Kafka Streams** | Powerful streaming semantics | Requires a Kafka cluster; not native to GCP; significant operational overhead |

## Rationale

Beam provides a clean separation between the pipeline logic and the execution environment. Writing the ingestion code once with Beam means it can be promoted to Dataflow without code changes if data volumes grow — only the runner flag changes. The DirectRunner runs on the existing VM without additional GCP services or cost. Beam's native `ReadFromPubSub` and `WriteToBigQuery` IOs handle backpressure and batching automatically.

## Consequences

- **Positive:** Path to production scale is a one-flag change (`--runner DataflowRunner`); Pub/Sub-to-BigQuery latency is under 5 seconds in DirectRunner mode.
- **Negative:** Beam's programming model (PCollections, transforms) has a steeper learning curve than a simple for-loop consumer. DirectRunner is single-threaded and not suitable for high-throughput production workloads without moving to Dataflow.
