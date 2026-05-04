#!/bin/bash

PIPELINE_PATH="/home/jsteven_romeror_gmail_com/pipelines/ingestion/bronze/bronze_pipeline.py"
PROJECT_ID="pipeline-health-mon-2026"

# Matar todos los pipelines existentes
echo "Matando pipelines anteriores..."
pkill -f bronze_pipeline.py
sleep 5

mkdir -p ~/pipelines/bronze/logs

declare -A SCHEMAS

# Core (3)
SCHEMAS[customer_events]="event_id:STRING,customer_id:STRING,email:STRING,country:STRING,signup_date:TIMESTAMP,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[booking_events]="event_id:STRING,booking_id:STRING,customer_id:STRING,origin:STRING,destination:STRING,total_amount:FLOAT,status:STRING,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[payment_events]="event_id:STRING,payment_id:STRING,booking_id:STRING,customer_id:STRING,amount:FLOAT,currency:STRING,payment_method:STRING,status:STRING,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"

# Iniciales (7)
SCHEMAS[search_events]="event_id:STRING,customer_id:STRING,origin:STRING,destination:STRING,search_date:TIMESTAMP,passengers:INTEGER,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[hotel_events]="event_id:STRING,booking_id:STRING,customer_id:STRING,hotel_id:STRING,hotel_name:STRING,checkin_date:TIMESTAMP,checkout_date:TIMESTAMP,room_price:FLOAT,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[flight_events]="event_id:STRING,booking_id:STRING,customer_id:STRING,flight_number:STRING,origin:STRING,destination:STRING,departure_time:TIMESTAMP,ticket_price:FLOAT,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[cancellation_events]="event_id:STRING,booking_id:STRING,customer_id:STRING,cancellation_reason:STRING,refund_amount:FLOAT,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[review_events]="event_id:STRING,booking_id:STRING,customer_id:STRING,rating:INTEGER,review_text:STRING,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[support_events]="event_id:STRING,ticket_id:STRING,customer_id:STRING,issue_type:STRING,priority:STRING,status:STRING,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[marketing_events]="event_id:STRING,customer_id:STRING,campaign_id:STRING,channel:STRING,action:STRING,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"

# Nuevas (15)
SCHEMAS[loyalty_events]="event_id:STRING,customer_id:STRING,loyalty_tier:STRING,points_earned:INTEGER,points_redeemed:INTEGER,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[session_events]="event_id:STRING,session_id:STRING,customer_id:STRING,device_type:STRING,browser:STRING,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[device_events]="event_id:STRING,customer_id:STRING,device_id:STRING,device_type:STRING,os:STRING,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[location_events]="event_id:STRING,customer_id:STRING,country:STRING,city:STRING,latitude:FLOAT,longitude:FLOAT,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[itinerary_events]="event_id:STRING,booking_id:STRING,customer_id:STRING,origin:STRING,destination:STRING,travel_date:TIMESTAMP,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[baggage_events]="event_id:STRING,booking_id:STRING,customer_id:STRING,bags_count:INTEGER,baggage_fee:FLOAT,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[seat_events]="event_id:STRING,booking_id:STRING,customer_id:STRING,seat_number:STRING,seat_type:STRING,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[insurance_events]="event_id:STRING,booking_id:STRING,customer_id:STRING,insurance_type:STRING,insurance_cost:FLOAT,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[promo_events]="event_id:STRING,customer_id:STRING,promo_code:STRING,discount_amount:FLOAT,campaign_id:STRING,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[notification_events]="event_id:STRING,customer_id:STRING,notification_type:STRING,channel:STRING,status:STRING,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[refund_events]="event_id:STRING,payment_id:STRING,booking_id:STRING,customer_id:STRING,refund_amount:FLOAT,refund_reason:STRING,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[invoice_events]="event_id:STRING,booking_id:STRING,customer_id:STRING,invoice_id:STRING,total_amount:FLOAT,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[partner_events]="event_id:STRING,booking_id:STRING,partner_id:STRING,partner_type:STRING,commission_amount:FLOAT,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[fraud_events]="event_id:STRING,customer_id:STRING,payment_id:STRING,risk_score:FLOAT,fraud_flag:BOOLEAN,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"
SCHEMAS[agency_events]="event_id:STRING,booking_id:STRING,agency_id:STRING,agent_id:STRING,agency_commission:FLOAT,event_timestamp:TIMESTAMP,ingested_at:TIMESTAMP"

# Arrancar todos
for TABLE in "${!SCHEMAS[@]}"; do
  SUB="${TABLE//_/-}-sub"
  SCHEMA="${SCHEMAS[$TABLE]}"

  nohup python "$PIPELINE_PATH" \
    --subscription "projects/$PROJECT_ID/subscriptions/$SUB" \
    --table "$PROJECT_ID:bronze.$TABLE" \
    --schema "$SCHEMA" \
    > ~/pipelines/bronze/logs/${TABLE}.log 2>&1 &

  echo "  ✓ $TABLE"
  sleep 1
done

echo ""
echo "Esperando 5 segundos..."
sleep 5
echo ""
echo "Pipelines activos: $(ps aux | grep bronze_pipeline | grep -v grep | wc -l) / 25"
