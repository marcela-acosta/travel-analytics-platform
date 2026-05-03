SELECT
  'payment' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_payment_events') }}

UNION ALL

SELECT
  'invoice' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_invoice_events') }}

UNION ALL

SELECT
  'refund' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_refund_events') }}

UNION ALL

SELECT
  'promo' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_promo_events') }}

UNION ALL

SELECT
  'insurance' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_insurance_events') }}

UNION ALL

SELECT
  'cancellation' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_cancellation_events') }}
