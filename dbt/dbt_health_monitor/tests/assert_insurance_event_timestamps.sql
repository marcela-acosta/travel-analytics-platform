{{ config(severity='warn') }}

-- fails when insurance event timestamps are inconsistent
select *
from {{ ref('slv_insurance_events') }}
where ingested_at is not null
  and staged_at < ingested_at
