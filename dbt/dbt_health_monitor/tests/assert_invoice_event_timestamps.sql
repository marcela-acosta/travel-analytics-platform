{{ config(severity='warn') }}

-- fails when invoice event timestamps are inconsistent
select *
from {{ ref('slv_invoice_events') }}
where ingested_at is not null
  and staged_at < ingested_at
