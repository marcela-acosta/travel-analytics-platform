{{ config(severity='warn') }}

-- fails if won_opportunities exceeds total_opportunities in either conversion model
select agent as entity, won_opportunities, total_opportunities
from {{ ref('gld_conversion_by_agent') }}
where won_opportunities > total_opportunities

union all

select product as entity, won_opportunities, total_opportunities
from {{ ref('gld_conversion_by_product') }}
where won_opportunities > total_opportunities
