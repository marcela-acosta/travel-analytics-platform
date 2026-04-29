-- fails when partner event timestamps are inconsistent
select *
from {{ ref('slv_partner_events') }}
where ingested_at is not null
  and staged_at < ingested_at
