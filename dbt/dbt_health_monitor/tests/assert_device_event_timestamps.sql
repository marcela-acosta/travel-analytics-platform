-- fails when device event timestamps are inconsistent
select *
from {{ ref('slv_device_events') }}
where ingested_at is not null
  and staged_at < ingested_at
