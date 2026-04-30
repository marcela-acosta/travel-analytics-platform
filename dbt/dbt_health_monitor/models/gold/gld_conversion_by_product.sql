{{ config(tags=["gold"]) }}

select
    product,
    count(*) as total_opportunities,
    countif(stage = 'Won') as won_opportunities,
    countif(stage = 'Lost') as lost_opportunities,
    coalesce(round(
        safe_divide(
            countif(stage = 'Won'),
            countif(stage in ('Won', 'Lost'))
        ) * 100,
        2
    ), 0) as win_rate_pct,
    sum(value) as total_pipeline_value,
    sum(case when stage = 'Won' then value else 0 end) as won_value
from {{ ref('gld_dashboard_opportunities') }}
group by product