# dbt_health_monitor

Starter dbt project for BigQuery using medallion architecture.

## Architecture

- `models/staging`: typed, source-aligned views over bronze
- `models/silver`: cleaned, normalized, deduplicated event tables
- `models/gold`: business-ready marts and metrics

## Silver layer

The silver layer currently includes curated models for booking, cancellation, CRM, customer, flight, hotel, marketing, payment, review, search, support, agency, baggage, device, fraud, insurance, invoice, itinerary, location, loyalty, notification, partner, promo, refund, seat, and session events.

These models standardize text casing where needed, keep opaque event snapshots as JSON payloads, and retain the latest record per business key or row hash.

## BigQuery setup

1. Copy `profiles.yml.example` into your dbt profiles directory (`~/.dbt/profiles.yml`).
2. Replace placeholders with your GCP project, dataset, and service account path.
3. Install dependencies:

```bash
dbt deps
```

## Quick start

```bash
cd dbt/dbt_health_monitor
dbt debug
dbt build
```

## Included tests

- Generic tests in model schema files (`not_null`, `unique`, `accepted_values`)
- Package test (`dbt_utils.unique_combination_of_columns`)
- Singular SQL data tests in `tests/`
- Support payload integrity check for the opaque JSON event snapshot
