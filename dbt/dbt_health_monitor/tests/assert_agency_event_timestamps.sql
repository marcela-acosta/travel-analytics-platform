{{ config(severity='warn') }}

-- fails when agency event timestamps are inconsistent
select *
from {{ ref('slv_agency_events') }}
where ingested_at is not null
  and staged_at < ingested_at
