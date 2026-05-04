#!/bin/bash
PROJECT="pipeline-health-mon-2026"
DATASET="bronze"

TABLES=(
  customer_events booking_events payment_events
  search_events hotel_events flight_events
  cancellation_events review_events support_events marketing_events
  loyalty_events session_events device_events location_events
  itinerary_events baggage_events seat_events insurance_events
  promo_events notification_events refund_events invoice_events
  partner_events fraud_events agency_events
)

echo "================================================"
echo "  BRONZE LAYER — VERIFICACIÓN DE REGISTROS"
echo "  $(date)"
echo "================================================"

TOTAL=0
TABLAS_OK=0
TABLAS_BAJAS=0

for TABLE in "${TABLES[@]}"; do
  RAW=$(bq query --use_legacy_sql=false --format=csv --quiet \
    "SELECT COUNT(*) as cnt FROM \`$PROJECT.$DATASET.$TABLE\`" 2>/dev/null)
  COUNT=$(echo "$RAW" | tail -1 | tr -d ',' | tr -d ' ' | tr -d '\r')

  # Si no es número, poner 0
  if ! [[ "$COUNT" =~ ^[0-9]+$ ]]; then
    COUNT=0
  fi

  TOTAL=$((TOTAL + COUNT))

  if [ "$COUNT" -ge 90000 ]; then
    STATUS="OK "
    TABLAS_OK=$((TABLAS_OK + 1))
  elif [ "$COUNT" -ge 50000 ]; then
    STATUS="MED"
    TABLAS_BAJAS=$((TABLAS_BAJAS + 1))
  else
    STATUS="LOW"
    TABLAS_BAJAS=$((TABLAS_BAJAS + 1))
  fi

  printf "  [%s] %-30s %s registros\n" "$STATUS" "$TABLE" "$COUNT"
done

echo "================================================"
echo "  Tablas >= 90k:   $TABLAS_OK / 25"
echo "  Tablas bajas:    $TABLAS_BAJAS / 25"
echo "  TOTAL REGISTROS: $TOTAL"
echo "================================================"
