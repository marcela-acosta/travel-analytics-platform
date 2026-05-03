SELECT
  'flight' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_flight_events') }}

UNION ALL

SELECT
  'hotel' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_hotel_events') }}

UNION ALL

SELECT
  'baggage' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_baggage_events') }}

UNION ALL

SELECT
  'seat' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_seat_events') }}

UNION ALL

SELECT
  'itinerary' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_itinerary_events') }}

UNION ALL

SELECT
  'location' AS domain,
  COUNT(*) AS total_events,
  MIN(ingested_at) AS first_ingested_at,
  MAX(ingested_at) AS last_ingested_at,
  MAX(staged_at) AS last_staged_at
FROM {{ ref('slv_location_events') }}
