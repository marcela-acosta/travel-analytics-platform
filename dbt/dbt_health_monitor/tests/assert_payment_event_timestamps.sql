{{ config(severity='warn') }}

-- fails when payment event timestamps are inconsistent
select *
from {{ ref('slv_payment_events') }}
where ingested_at is not null
  and staged_at < ingested_at
