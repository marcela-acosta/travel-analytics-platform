SELECT
  'marketing' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_marketing_events') }}

UNION ALL

SELECT
  'notification' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_notification_events') }}

UNION ALL

SELECT
  'review' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_review_events') }}

UNION ALL

SELECT
  'support' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_support_events') }}

UNION ALL

SELECT
  'search' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_search_events') }}

UNION ALL

SELECT
  'session' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_session_events') }}

UNION ALL

SELECT
  'device' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_device_events') }}

UNION ALL

SELECT
  'loyalty' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_loyalty_events') }}
