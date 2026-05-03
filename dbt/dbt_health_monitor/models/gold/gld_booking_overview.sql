SELECT
  booking_status,
  channel,
  currency,
  COUNT(*) AS total_bookings,
  SUM(total_amount) AS total_booking_amount,
  AVG(total_amount) AS avg_booking_amount,
  COUNT(DISTINCT customer_id) AS distinct_customers,
  MAX(updated_at) AS latest_booking_updated_at
FROM {{ ref('slv_booking_events') }}
GROUP BY
  booking_status,
  channel,
  currency
