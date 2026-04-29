#!/bin/bash

PROJECT_ID="pipeline-health-mon-2026"

generate_uuid() {
  cat /proc/sys/kernel/random/uuid
}

timestamp_now() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

for i in {1..10}
do
  echo "Publishing batch $i..."

  gcloud pubsub topics publish loyalty-events --message="$(cat <<EOF
{"event_id":"$(generate_uuid)","customer_id":"CUST_$i","loyalty_tier":"GOLD","points_earned":100,"points_redeemed":10,"event_timestamp":"$(timestamp_now)"}
EOF
)"

  gcloud pubsub topics publish session-events --message="$(cat <<EOF
{"event_id":"$(generate_uuid)","session_id":"SESSION_$i","customer_id":"CUST_$i","device_type":"mobile","browser":"chrome","event_timestamp":"$(timestamp_now)"}
EOF
)"

  gcloud pubsub topics publish device-events --message="$(cat <<EOF
{"event_id":"$(generate_uuid)","customer_id":"CUST_$i","device_id":"DEV_$i","device_type":"mobile","os":"android","event_timestamp":"$(timestamp_now)"}
EOF
)"

  gcloud pubsub topics publish location-events --message="$(cat <<EOF
{"event_id":"$(generate_uuid)","customer_id":"CUST_$i","country":"MX","city":"CDMX","latitude":19.43,"longitude":-99.13,"event_timestamp":"$(timestamp_now)"}
EOF
)"

  gcloud pubsub topics publish itinerary-events --message="$(cat <<EOF
{"event_id":"$(generate_uuid)","booking_id":"BOOK_$i","customer_id":"CUST_$i","origin":"MEX","destination":"CUN","travel_date":"2026-05-01","event_timestamp":"$(timestamp_now)"}
EOF
)"

  gcloud pubsub topics publish baggage-events --message="$(cat <<EOF
{"event_id":"$(generate_uuid)","booking_id":"BOOK_$i","customer_id":"CUST_$i","bags_count":2,"baggage_fee":50.0,"event_timestamp":"$(timestamp_now)"}
EOF
)"

  gcloud pubsub topics publish seat-events --message="$(cat <<EOF
{"event_id":"$(generate_uuid)","booking_id":"BOOK_$i","customer_id":"CUST_$i","seat_number":"12A","seat_type":"window","event_timestamp":"$(timestamp_now)"}
EOF
)"

  gcloud pubsub topics publish insurance-events --message="$(cat <<EOF
{"event_id":"$(generate_uuid)","booking_id":"BOOK_$i","customer_id":"CUST_$i","insurance_type":"basic","insurance_cost":20.0,"event_timestamp":"$(timestamp_now)"}
EOF
)"

  gcloud pubsub topics publish promo-events --message="$(cat <<EOF
{"event_id":"$(generate_uuid)","customer_id":"CUST_$i","promo_code":"PROMO10","discount_amount":10.0,"campaign_id":"CMP_$i","event_timestamp":"$(timestamp_now)"}
EOF
)"

  gcloud pubsub topics publish notification-events --message="$(cat <<EOF
{"event_id":"$(generate_uuid)","customer_id":"CUST_$i","notification_type":"email","channel":"email","status":"sent","event_timestamp":"$(timestamp_now)"}
EOF
)"

  gcloud pubsub topics publish refund-events --message="$(cat <<EOF
{"event_id":"$(generate_uuid)","payment_id":"PAY_$i","booking_id":"BOOK_$i","customer_id":"CUST_$i","refund_amount":30.0,"refund_reason":"cancellation","event_timestamp":"$(timestamp_now)"}
EOF
)"

  gcloud pubsub topics publish invoice-events --message="$(cat <<EOF
{"event_id":"$(generate_uuid)","booking_id":"BOOK_$i","customer_id":"CUST_$i","invoice_id":"INV_$i","total_amount":200.0,"event_timestamp":"$(timestamp_now)"}
EOF
)"

  gcloud pubsub topics publish partner-events --message="$(cat <<EOF
{"event_id":"$(generate_uuid)","booking_id":"BOOK_$i","partner_id":"PARTNER_$i","partner_type":"hotel","commission_amount":15.0,"event_timestamp":"$(timestamp_now)"}
EOF
)"

  gcloud pubsub topics publish fraud-events --message="$(cat <<EOF
{"event_id":"$(generate_uuid)","customer_id":"CUST_$i","payment_id":"PAY_$i","risk_score":0.2,"fraud_flag":false,"event_timestamp":"$(timestamp_now)"}
EOF
)"

  gcloud pubsub topics publish agency-events --message="$(cat <<EOF
{"event_id":"$(generate_uuid)","booking_id":"BOOK_$i","agency_id":"AG_$i","agent_id":"AGENT_$i","agency_commission":25.0,"event_timestamp":"$(timestamp_now)"}
EOF
)"

done

echo "✅ Done: 10 records sent to each of the 15 tables"
