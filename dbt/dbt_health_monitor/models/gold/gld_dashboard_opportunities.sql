{{ config(tags=["gold"], materialized="view") }}

with silver as (
    select *
    from {{ ref('slv_crm_events') }}
),

normalized as (
    select
        opportunity_id,

        case lower(stage)
            when 'prospección' then 'Prospecting'
            when 'prospecting' then 'Prospecting'
            when 'calificado' then 'Qualified'
            when 'qualified' then 'Qualified'
            when 'propuesta' then 'Proposal'
            when 'proposal' then 'Proposal'
            when 'negociación' then 'Negotiation'
            when 'negociacion' then 'Negotiation'
            when 'negotiation' then 'Negotiation'
            when 'ganado' then 'Won'
            when 'won' then 'Won'
            when 'perdido' then 'Lost'
            when 'lost' then 'Lost'
            else initcap(stage)
        end as stage,

        region,

        case lower(product)
            when 'vuelo' then 'Flight'
            when 'flight' then 'Flight'
            when 'hotel' then 'Hotel'
            when 'auto' then 'Car Rental'
            when 'car' then 'Car Rental'
            when 'car rental' then 'Car Rental'
            when 'paquete_2x' then 'Package 2x'
            when 'package 2x' then 'Package 2x'
            when 'paquete_3x' then 'Package 3x'
            when 'package 3x' then 'Package 3x'
            else initcap(product)
        end as product,

        case
            when regexp_contains(lower(agent_id), r'agent[_ -]?\d+')
                then concat(
                    'Agent ',
                    lpad(regexp_extract(lower(agent_id), r'(\d+)'), 2, '0')
                )
            else agent_id
        end as agent,

        value,
        expected_close_date,
        updated_at,
        ingested_at,
        staged_at,

        date_diff(current_date(), date(updated_at), day) as days_since_update,
        date_diff(expected_close_date, current_date(), day) as days_until_expected_close,

        case
            when stage in ('Won', 'Lost') then false
            -- not updated in 14+ days
            when date_diff(current_date(), date(updated_at), day) >= 14 then true
            -- expected close within 30 days but still in active stage (at risk)
            when date_diff(expected_close_date, current_date(), day) <= 30 then true
            else false
        end as is_stale

    from silver
    where opportunity_id is not null
)

select *
from normalized
