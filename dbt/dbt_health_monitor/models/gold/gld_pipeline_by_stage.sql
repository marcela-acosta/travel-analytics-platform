{{ config(tags=["gold"]) }}

select
    stage,
    count(*) as total_opportunities,
    sum(value) as total_value,
    avg(value) as avg_opportunity_value,
    avg(days_since_update) as avg_days_since_update,
    countif(is_stale) as stale_opportunities
from {{ ref('gld_dashboard_opportunities') }}
group by stage
