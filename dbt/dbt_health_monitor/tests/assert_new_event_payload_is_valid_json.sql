{{ config(severity='warn') }}

-- fails when any new silver event payload is not valid JSON
with all_new_events as (
  select 'slv_cancellation_events' as model_name, event_payload
  from {{ ref('slv_cancellation_events') }}

  union all

  select 'slv_flight_events' as model_name, event_payload
  from {{ ref('slv_flight_events') }}

  union all

  select 'slv_hotel_events' as model_name, event_payload
  from {{ ref('slv_hotel_events') }}

  union all

  select 'slv_marketing_events' as model_name, event_payload
  from {{ ref('slv_marketing_events') }}

  union all

  select 'slv_payment_events' as model_name, event_payload
  from {{ ref('slv_payment_events') }}

  union all

  select 'slv_review_events' as model_name, event_payload
  from {{ ref('slv_review_events') }}

  union all

  select 'slv_search_events' as model_name, event_payload
  from {{ ref('slv_search_events') }}

  union all

  select 'slv_support_events' as model_name, event_payload
  from {{ ref('slv_support_events') }}

  union all

  select 'slv_agency_events' as model_name, event_payload
  from {{ ref('slv_agency_events') }}

  union all

  select 'slv_baggage_events' as model_name, event_payload
  from {{ ref('slv_baggage_events') }}

  union all

  select 'slv_device_events' as model_name, event_payload
  from {{ ref('slv_device_events') }}

  union all

  select 'slv_fraud_events' as model_name, event_payload
  from {{ ref('slv_fraud_events') }}

  union all

  select 'slv_insurance_events' as model_name, event_payload
  from {{ ref('slv_insurance_events') }}

  union all

  select 'slv_invoice_events' as model_name, event_payload
  from {{ ref('slv_invoice_events') }}

  union all

  select 'slv_itinerary_events' as model_name, event_payload
  from {{ ref('slv_itinerary_events') }}

  union all

  select 'slv_location_events' as model_name, event_payload
  from {{ ref('slv_location_events') }}

  union all

  select 'slv_loyalty_events' as model_name, event_payload
  from {{ ref('slv_loyalty_events') }}

  union all

  select 'slv_notification_events' as model_name, event_payload
  from {{ ref('slv_notification_events') }}

  union all

  select 'slv_partner_events' as model_name, event_payload
  from {{ ref('slv_partner_events') }}

  union all

  select 'slv_promo_events' as model_name, event_payload
  from {{ ref('slv_promo_events') }}

  union all

  select 'slv_refund_events' as model_name, event_payload
  from {{ ref('slv_refund_events') }}

  union all

  select 'slv_seat_events' as model_name, event_payload
  from {{ ref('slv_seat_events') }}

  union all

  select 'slv_session_events' as model_name, event_payload
  from {{ ref('slv_session_events') }}
)

select *
from all_new_events
where event_payload is null
  or safe.parse_json(event_payload) is null
