{{
  config(
    tags=["silver"],
    materialized="incremental",
    unique_key="customer_id",
    on_schema_change="append_new_columns"
  )
}}

with staged as (
  select *
  from {{ ref('stg_customer_events') }}
  {%- if is_incremental() %}
    where ingested_at > (select coalesce(max(ingested_at), timestamp('1900-01-01')) from {{ this }})
  {%- endif %}
), transformed as (
  select
    row_hash as customer_event_sk,
    staged_at,
    nullif(trim(customer_id), '') as customer_id,
    nullif(trim(full_name), '') as full_name,
    lower(nullif(trim(email), '')) as email,
    nullif(trim(phone), '') as phone,
    upper(nullif(trim(country), '')) as country,
    nullif(trim(city), '') as city,
    lower(nullif(trim(customer_segment), '')) as customer_segment,
    lower(nullif(trim(loyalty_tier), '')) as loyalty_tier,
    safe_cast(nullif(trim(created_at), '') as timestamp) as created_at,
    safe_cast(nullif(trim(updated_at), '') as timestamp) as updated_at,
    ingested_at
  from staged
)

select *
from transformed
qualify row_number() over (
  partition by customer_id
  order by updated_at desc, created_at desc, ingested_at desc, staged_at desc
) = 1
