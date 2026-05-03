{{ config(severity='warn') }}

-- fails when location event timestamps are inconsistent
select *
from {{ ref('slv_location_events') }}
where ingested_at is not null
  and staged_at < ingested_at
