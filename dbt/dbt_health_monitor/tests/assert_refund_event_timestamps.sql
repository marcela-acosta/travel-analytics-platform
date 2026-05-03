{{ config(severity='warn') }}

-- fails when refund event timestamps are inconsistent
select *
from {{ ref('slv_refund_events') }}
where ingested_at is not null
  and staged_at < ingested_at
