{{ config(tags=["staging"]) }}

select
  to_hex(md5(to_json_string(src))) as row_hash,
  current_timestamp() as staged_at,
  src.*
from {{ source('bronze', 'insurance_events') }} as src
