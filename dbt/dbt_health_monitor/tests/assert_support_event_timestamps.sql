{{ config(severity='warn') }}

-- fails when support event timestamps are inconsistent
select *
from {{ ref('slv_support_events') }}
where ingested_at is not null
  and staged_at < ingested_at
