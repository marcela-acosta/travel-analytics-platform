{{ config(tags=["staging"]) }}

select
  to_hex(md5(to_json_string(src))) as row_hash,
  current_timestamp() as staged_at,
  src.*
from {{ source('bronze', 'agency_events') }} as src
