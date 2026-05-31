{% snapshot customer_scd2 %}

{{
    config(
        target_schema='silver',
        unique_key='customer_id',
        strategy='check',
        check_cols=['full_name', 'segment', 'status', 'city'],
        invalidate_hard_deletes=True
    )
}}

select
    customer_id,
    full_name,
    phone_hash,
    email_hash,
    birth_date,
    city,
    segment,
    registration_date,
    status,
    source_system,
    bronze_loaded_at,
    updated_at
from {{ ref('dim_customer') }}

{% endsnapshot %}
