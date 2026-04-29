-- fails when support event payload metadata is missing or malformed
select *
from {{ ref('slv_support_events') }}
where event_payload is null
   or safe.parse_json(event_payload) is null
   or json_value(safe.parse_json(event_payload), '$.ingested_at') is null
   or json_value(safe.parse_json(event_payload), '$.staged_at') is null