{{ config(
    order_by='(trx_date, customer_id, trx_id)',
    engine='ReplacingMergeTree(updated_at)',
    partition_by='toYYYYMM(trx_date)'
) }}

with source as (
    select * from {{ source('bronze', 'payments_transactions_raw') }}
),

cleaned as (
    select
        trx_id,
        account_id,
        customer_id,
        card_id,
        coalesce(trx_datetime, toDateTime(posting_date)) as trx_datetime,
        assumeNotNull(toDate(coalesce(trx_datetime, toDateTime(posting_date)))) as trx_date,
        nullIf(trimBoth(trx_type), '') as trx_type,
        amount,
        nullIf(trimBoth(currency), '') as currency,
        nullIf(trimBoth(channel), '') as channel,
        merchant_category_code,
        nullIf(trimBoth(counterparty_name), '') as counterparty_name,
        nullIf(trimBoth(status), '') as status,
        posting_date,
        source_system,
        load_dttm as bronze_loaded_at
    from source
    where trx_id > 0
      and customer_id > 0
      and account_id != ''
      and coalesce(trx_datetime, toDateTime(posting_date)) is not null
),

deduped as (
    select
        trx_id,
        account_id,
        customer_id,
        card_id,
        trx_datetime,
        trx_date,
        trx_type,
        amount,
        currency,
        channel,
        merchant_category_code,
        counterparty_name,
        status,
        posting_date,
        source_system,
        bronze_loaded_at,
        now() as updated_at
    from cleaned
    qualify row_number() over (
        partition by trx_id, source_system
        order by bronze_loaded_at desc
    ) = 1
)

select * from deduped
