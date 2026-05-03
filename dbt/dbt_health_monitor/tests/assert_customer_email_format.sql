{{ config(severity='warn') }}

-- fails when email is present but does not contain a basic user@domain format
select *
from {{ ref('slv_customer_events') }}
where email is not null
  and not regexp_contains(email, r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
