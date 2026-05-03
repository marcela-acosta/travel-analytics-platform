{{ config(severity='warn') }}

-- fails when promo event timestamps are inconsistent
select *
from {{ ref('slv_promo_events') }}
where ingested_at is not null
  and staged_at < ingested_at
