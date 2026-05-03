{{ config(severity='warn') }}

-- fails when marketing event timestamps are inconsistent
select *
from {{ ref('slv_marketing_events') }}
where ingested_at is not null
  and staged_at < ingested_at
