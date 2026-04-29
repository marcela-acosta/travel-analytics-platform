-- fails when seat event timestamps are inconsistent
select *
from {{ ref('slv_seat_events') }}
where ingested_at is not null
  and staged_at < ingested_at
