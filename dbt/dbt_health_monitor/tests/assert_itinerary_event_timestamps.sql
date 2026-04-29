-- fails when itinerary event timestamps are inconsistent
select *
from {{ ref('slv_itinerary_events') }}
where ingested_at is not null
  and staged_at < ingested_at
