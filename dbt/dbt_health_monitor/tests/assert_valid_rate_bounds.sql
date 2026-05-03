{{ config(severity='warn') }}

-- fails if success+failed exceeds total
select *
from {{ ref('fct_pipeline_health') }}
where successful_runs + failed_runs > total_runs
