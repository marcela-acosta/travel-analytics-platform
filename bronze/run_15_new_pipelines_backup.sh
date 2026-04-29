#!/bin/bash

PROJECT_ID="pipeline-health-mon-2026"
DATASET="bronze"

declare -A TABLES

TABLES[loyalty_events]="event_id:STRING,customer_id:STRING,loyalty_tier:STRING,points_earned:INTEGER,points_redeemed:INTEGER,event_timestamp:TIMESTAMP"
TABLES[session_events]="event_id:STRING,session_id:STRING,customer_id:STRING,device_type:STRING,browser:STRING,event_timestamp:TIMESTAMP"
TABLES[device_events]="event_id:STRING,customer_id:STRING,device_id:STRING,device_type:STRING,os:STRING,event_timestamp:TIMESTAMP"
TABLES[location_events]="event_id:STRING,customer_id:STRING,country:STRING,city:STRING,latitude:FLOAT,longitude:FLOAT,event_timestamp:TIMESTAMP"
TABLES[itinerary_events]="event_id:STRING,booking_id:STRING,customer_id:STRING,origin:STRING,destination:STRING,travel_date:DATE,event_timestamp:TIMESTAMP"
TABLES[baggage_events]="event_id:STRING,booking_id:STRING,customer_id:STRING,bags_count:INTEGER,baggage_fee:FLOAT,event_timestamp:TIMESTAMP"
TABLES[seat_events]="event_id:STRING,booking_id:STRING,customer_id:STRING,seat_number:STRING,seat_type:STRING,event_timestamp:TIMESTAMP"
TABLES[insurance_events]="event_id:STRING,booking_id:STRING,customer_id:STRING,insurance_type:STRING,insurance_cost:FLOAT,event_timestamp:TIMESTAMP"
TABLES[promo_events]="event_id:STRING,customer_id:STRING,promo_code:STRING,discount_amount:FLOAT,campaign_id:STRING,event_timestamp:TIMESTAMP"
TABLES[notification_events]="event_id:STRING,customer_id:STRING,notification_type:STRING,channel:STRING,status:STRING,event_timestamp:TIMESTAMP"
TABLES[refund_events]="event_id:STRING,payment_id:STRING,booking_id:STRING,customer_id:STRING,refund_amount:FLOAT,refund_reason:STRING,event_timestamp:TIMESTAMP"
TABLES[invoice_events]="event_id:STRING,booking_id:STRING,customer_id:STRING,invoice_id:STRING,total_amount:FLOAT,event_timestamp:TIMESTAMP"
TABLES[partner_events]="event_id:STRING,booking_id:STRING,partner_id:STRING,partner_type:STRING,commission_amount:FLOAT,event_timestamp:TIMESTAMP"
TABLES[fraud_events]="event_id:STRING,customer_id:STRING,payment_id:STRING,risk_score:FLOAT,fraud_flag:BOOLEAN,event_timestamp:TIMESTAMP"
TABLES[agency_events]="event_id:STRING,booking_id:STRING,agency_id:STRING,agent_id:STRING,agency_commission:FLOAT,event_timestamp:TIMESTAMP"

for TABLE in "${!TABLES[@]}"
do
  TOPIC="${TABLE//_/-}"
  SUBSCRIPTION="${TOPIC}-sub"
  SCHEMA="${TABLES[$TABLE]}"

  echo "Starting pipeline for $TABLE"

  nohup python bronze_pipeline.py \
    --subscription "projects/$PROJECT_ID/subscriptions/$SUBSCRIPTION" \
    --table "$PROJECT_ID:$DATASET.$TABLE" \
    --schema "$SCHEMA" \
    > "logs/${TABLE}.log" 2>&1 &

  sleep 2
done

echo "All 15 pipelines started."
