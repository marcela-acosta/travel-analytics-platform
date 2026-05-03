{{ config(severity='warn') }}

-- fails when flight event timestamps are inconsistent
select *
from {{ ref('slv_flight_events') }}
where ingested_at is not null
  and staged_at < ingested_at
