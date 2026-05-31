{{ config(
    order_by='account_id',
    engine='ReplacingMergeTree(updated_at)'
) }}

with source as (
    select * from {{ source('bronze', 'core_accounts_raw') }}
),

cleaned as (
    select
        account_id,
        customer_id,
        nullIf(trimBoth(product_type), '') as product_type,
        nullIf(trimBoth(currency), '') as currency,
        balance,
        opened_date,
        closed_date,
        nullIf(trimBoth(status), '') as status,
        source_system,
        load_dttm as bronze_loaded_at
    from source
    where account_id != ''
      and customer_id > 0
),

deduped as (
    select
        account_id,
        customer_id,
        product_type,
        currency,
        balance,
        opened_date,
        closed_date,
        status,
        source_system,
        bronze_loaded_at,
        now() as updated_at
    from cleaned
    qualify row_number() over (
        partition by account_id, source_system
        order by bronze_loaded_at desc
    ) = 1
)

select * from deduped
