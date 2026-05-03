{{ config(severity='warn') }}

-- fails when search event timestamps are inconsistent
select *
from {{ ref('slv_search_events') }}
where ingested_at is not null
  and staged_at < ingested_at
