#!/bin/bash

PROJECT_ID="pipeline-health-mon-2026"
DATASET="bronze"

TABLES=(
"agency_events"
"baggage_events"
"booking_events"
"cancellation_events"
"crm_events"
"customer_events"
"device_events"
"flight_events"
"fraud_events"
"hotel_events"
"insurance_events"
"invoice_events"
"itinerary_events"
"location_events"
"loyalty_events"
"marketing_events"
"notification_events"
"partner_events"
"payment_events"
"promo_events"
"refund_events"
"review_events"
"search_events"
"seat_events"
"session_events"
"support_events"
)

for TABLE in "${TABLES[@]}"
do
  echo "Updating $TABLE..."

  bq query --use_legacy_sql=false "
  ALTER TABLE \`$PROJECT_ID.$DATASET.$TABLE\`
  ADD COLUMN IF NOT EXISTS ingested_at TIMESTAMP
  "

done

echo "✅ All tables updated with ingested_at"
