{{
  config(
    tags=["silver"],
    materialized="incremental",
    unique_key="booking_id",
    on_schema_change="append_new_columns"
  )
}}

with staged as (
  select *
  from {{ ref('stg_booking_events') }}
  {%- if is_incremental() %}
    where ingested_at > (select coalesce(max(ingested_at), timestamp('1900-01-01')) from {{ this }})
  {%- endif %}
), transformed as (
  select
    row_hash as booking_event_sk,
    staged_at,
    nullif(trim(booking_id), '') as booking_id,
    nullif(trim(customer_id), '') as customer_id,
    safe_cast(nullif(trim(booking_date), '') as date) as booking_date,
    safe_cast(nullif(trim(travel_start_date), '') as date) as travel_start_date,
    safe_cast(nullif(trim(travel_end_date), '') as date) as travel_end_date,
    lower(nullif(trim(booking_status), '')) as booking_status,
    cast(total_amount as float64) as total_amount,
    upper(nullif(trim(currency), '')) as currency,
    nullif(trim(destination_city), '') as destination_city,
    upper(nullif(trim(destination_country), '')) as destination_country,
    lower(nullif(trim(channel), '')) as channel,
    safe_cast(nullif(trim(created_at), '') as timestamp) as created_at,
    safe_cast(nullif(trim(updated_at), '') as timestamp) as updated_at,
    ingested_at
  from staged
)

select *
from transformed
qualify row_number() over (
  partition by booking_id
  order by coalesce(updated_at, created_at) desc, ingested_at desc, staged_at desc
) = 1
