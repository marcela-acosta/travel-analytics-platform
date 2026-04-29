#!/bin/bash

PROJECT_ID="pipeline-health-mon-2026"

publish_msg () {
  TOPIC=$1
  MESSAGE=$2

  gcloud pubsub topics publish "$TOPIC" \
    --project="$PROJECT_ID" \
    --message="$MESSAGE"
}

for i in $(seq 1 10)
do
  TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  publish_msg "loyalty-events" "{\"event_id\":\"loyalty_$i\",\"customer_id\":\"CUST_$i\",\"loyalty_tier\":\"GOLD\",\"points_earned\":100,\"points_redeemed\":10,\"event_timestamp\":\"$TS\"}"

  publish_msg "session-events" "{\"event_id\":\"session_$i\",\"session_id\":\"SESSION_$i\",\"customer_id\":\"CUST_$i\",\"device_type\":\"mobile\",\"browser\":\"chrome\",\"event_timestamp\":\"$TS\"}"

  publish_msg "device-events" "{\"event_id\":\"device_$i\",\"customer_id\":\"CUST_$i\",\"device_id\":\"DEV_$i\",\"device_type\":\"mobile\",\"os\":\"android\",\"event_timestamp\":\"$TS\"}"

  publish_msg "location-events" "{\"event_id\":\"location_$i\",\"customer_id\":\"CUST_$i\",\"country\":\"MX\",\"city\":\"CDMX\",\"latitude\":19.43,\"longitude\":-99.13,\"event_timestamp\":\"$TS\"}"

  publish_msg "itinerary-events" "{\"event_id\":\"itinerary_$i\",\"booking_id\":\"BOOK_$i\",\"customer_id\":\"CUST_$i\",\"origin\":\"MEX\",\"destination\":\"CUN\",\"travel_date\":\"2026-05-01\",\"event_timestamp\":\"$TS\"}"

  publish_msg "baggage-events" "{\"event_id\":\"baggage_$i\",\"booking_id\":\"BOOK_$i\",\"customer_id\":\"CUST_$i\",\"bags_count\":2,\"baggage_fee\":50.0,\"event_timestamp\":\"$TS\"}"

  publish_msg "seat-events" "{\"event_id\":\"seat_$i\",\"booking_id\":\"BOOK_$i\",\"customer_id\":\"CUST_$i\",\"seat_number\":\"12A\",\"seat_type\":\"window\",\"event_timestamp\":\"$TS\"}"

  publish_msg "insurance-events" "{\"event_id\":\"insurance_$i\",\"booking_id\":\"BOOK_$i\",\"customer_id\":\"CUST_$i\",\"insurance_type\":\"basic\",\"insurance_cost\":20.0,\"event_timestamp\":\"$TS\"}"

  publish_msg "promo-events" "{\"event_id\":\"promo_$i\",\"customer_id\":\"CUST_$i\",\"promo_code\":\"PROMO10\",\"discount_amount\":10.0,\"campaign_id\":\"CMP_$i\",\"event_timestamp\":\"$TS\"}"

  publish_msg "notification-events" "{\"event_id\":\"notification_$i\",\"customer_id\":\"CUST_$i\",\"notification_type\":\"email\",\"channel\":\"email\",\"status\":\"sent\",\"event_timestamp\":\"$TS\"}"

  publish_msg "refund-events" "{\"event_id\":\"refund_$i\",\"payment_id\":\"PAY_$i\",\"booking_id\":\"BOOK_$i\",\"customer_id\":\"CUST_$i\",\"refund_amount\":30.0,\"refund_reason\":\"cancellation\",\"event_timestamp\":\"$TS\"}"

  publish_msg "invoice-events" "{\"event_id\":\"invoice_$i\",\"booking_id\":\"BOOK_$i\",\"customer_id\":\"CUST_$i\",\"invoice_id\":\"INV_$i\",\"total_amount\":200.0,\"event_timestamp\":\"$TS\"}"

  publish_msg "partner-events" "{\"event_id\":\"partner_$i\",\"booking_id\":\"BOOK_$i\",\"partner_id\":\"PARTNER_$i\",\"partner_type\":\"hotel\",\"commission_amount\":15.0,\"event_timestamp\":\"$TS\"}"

  publish_msg "fraud-events" "{\"event_id\":\"fraud_$i\",\"customer_id\":\"CUST_$i\",\"payment_id\":\"PAY_$i\",\"risk_score\":0.2,\"fraud_flag\":false,\"event_timestamp\":\"$TS\"}"

  publish_msg "agency-events" "{\"event_id\":\"agency_$i\",\"booking_id\":\"BOOK_$i\",\"agency_id\":\"AG_$i\",\"agent_id\":\"AGENT_$i\",\"agency_commission\":25.0,\"event_timestamp\":\"$TS\"}"

done

echo "Done. Published 10 messages to each new topic."
