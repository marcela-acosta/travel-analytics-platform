SELECT
  'partner' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_partner_events') }}

UNION ALL

SELECT
  'agency' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_agency_events') }}