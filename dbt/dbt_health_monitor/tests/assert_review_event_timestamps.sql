{{ config(severity='warn') }}

-- fails when review event timestamps are inconsistent
select *
from {{ ref('slv_review_events') }}
where ingested_at is not null
  and staged_at < ingested_at
