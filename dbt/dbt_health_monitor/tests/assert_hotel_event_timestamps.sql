{{ config(severity='warn') }}

-- fails when hotel event timestamps are inconsistent
select *
from {{ ref('slv_hotel_events') }}
where ingested_at is not null
  and staged_at < ingested_at
