{{ config(tags=["silver"]) }}

with staged as (
  select *
  from {{ ref('stg_crm_events') }}
), transformed as (
  select
    row_hash as crm_event_sk,
    staged_at,
    nullif(trim(opportunity_id), '') as opportunity_id,
    lower(nullif(trim(stage), '')) as stage,
    nullif(trim(agent_id), '') as agent_id,
    nullif(trim(product), '') as product,
    cast(value as float64) as value,
    upper(nullif(trim(region), '')) as region,
    date(safe_cast(nullif(trim(expected_close_date), '') as timestamp)) as expected_close_date,
    safe_cast(nullif(trim(updated_at), '') as timestamp) as updated_at,
    ingested_at
  from staged
)

select *
from transformed
qualify row_number() over (
  partition by opportunity_id
  order by updated_at desc, ingested_at desc, staged_at desc
) = 1
