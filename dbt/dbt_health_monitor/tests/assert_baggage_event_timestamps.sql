-- fails when baggage event timestamps are inconsistent
select *
from {{ ref('slv_baggage_events') }}
where ingested_at is not null
  and staged_at < ingested_at
