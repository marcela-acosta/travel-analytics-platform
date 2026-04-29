{{ config(tags=["silver"]) }}

with staged as (
  select *
  from {{ ref('stg_fraud_events') }}
), transformed as (
  select
    row_hash as fraud_event_sk,
    staged_at,
    ingested_at,
    to_json_string(staged) as event_payload
  from staged
)

select *
from transformed
qualify row_number() over (
  partition by fraud_event_sk
  order by ingested_at desc, staged_at desc
) = 1
