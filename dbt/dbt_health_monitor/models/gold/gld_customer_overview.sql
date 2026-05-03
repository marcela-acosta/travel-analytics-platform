SELECT
  customer_segment,
  loyalty_tier,
  country,
  COUNT(*) AS total_customers,
  COUNTIF(email IS NOT NULL) AS customers_with_email,
  COUNTIF(phone IS NOT NULL) AS customers_with_phone,
  MAX(updated_at) AS latest_customer_updated_at
FROM {{ ref('slv_customer_events') }}
GROUP BY
  customer_segment,
  loyalty_tier,
  country
