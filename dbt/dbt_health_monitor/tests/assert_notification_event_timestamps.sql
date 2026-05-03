{{ config(severity='warn') }}

-- fails when notification event timestamps are inconsistent
select *
from {{ ref('slv_notification_events') }}
where ingested_at is not null
  and staged_at < ingested_at
