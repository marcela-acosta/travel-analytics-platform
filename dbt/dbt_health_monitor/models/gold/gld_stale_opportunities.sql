{{ config(tags=["gold"]) }}

select
    opportunity_id,
    stage,
    agent,
    product,
    region,
    value,
    expected_close_date,
    updated_at,
    days_since_update,
    days_until_expected_close,
    is_stale
from {{ ref('gld_dashboard_opportunities') }}
where is_stale = true
