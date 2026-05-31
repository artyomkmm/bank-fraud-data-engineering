{{ config(
    order_by='customer_id',
    engine='ReplacingMergeTree(updated_at)'
) }}

with source as (
    select * from {{ source('bronze', 'crm_customers_raw') }}
),

cleaned as (
    select
        customer_id,
        trimBoth(full_name) as full_name,
        nullIf(trimBoth(phone), '') as phone,
        nullIf(trimBoth(email), '') as email,
        birth_date,
        nullIf(trimBoth(city), '') as city,
        nullIf(trimBoth(segment), '') as segment,
        registration_date,
        nullIf(trimBoth(status), '') as status,
        source_system,
        load_dttm as bronze_loaded_at
    from source
    where customer_id > 0
),

hashed as (
    select
        customer_id,
        full_name,
        if(phone is null, null, {{ hash_pii('phone') }}) as phone_hash,
        if(email is null, null, {{ hash_pii('email') }}) as email_hash,
        birth_date,
        city,
        segment,
        registration_date,
        status,
        source_system,
        bronze_loaded_at
    from cleaned
),

deduped as (
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
        now() as updated_at
    from hashed
    qualify row_number() over (
        partition by customer_id, source_system
        order by bronze_loaded_at desc
    ) = 1
)

select * from deduped
