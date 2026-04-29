-- fails when session event timestamps are inconsistent
select *
from {{ ref('slv_session_events') }}
where ingested_at is not null
  and staged_at < ingested_at
