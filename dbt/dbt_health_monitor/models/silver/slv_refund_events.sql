{{
  config(
    tags=["silver"],
    materialized="incremental",
    unique_key="refund_event_sk",
    on_schema_change="append_new_columns"
  )
}}

with staged as (
  select *
  from {{ ref('stg_refund_events') }}
  {%- if is_incremental() %}
    where ingested_at > (select coalesce(max(ingested_at), timestamp('1900-01-01')) from {{ this }})
  {%- endif %}
), transformed as (
  select
    row_hash as refund_event_sk,
    staged_at,
    ingested_at,
    to_json_string(staged) as event_payload
  from staged
)

select *
from transformed
qualify row_number() over (
  partition by refund_event_sk
  order by ingested_at desc, staged_at desc
) = 1
