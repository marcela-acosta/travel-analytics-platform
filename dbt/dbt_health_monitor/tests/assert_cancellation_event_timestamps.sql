{{ config(severity='warn') }}

-- fails when cancellation event timestamps are inconsistent
select *
from {{ ref('slv_cancellation_events') }}
where ingested_at is not null
  and staged_at < ingested_at
