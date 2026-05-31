{{ config(
    order_by='(customer_id, trx_date)',
    engine='ReplacingMergeTree(refreshed_at)',
    partition_by='toYYYYMM(assumeNotNull(trx_date))'
) }}

select
    customer_id,
    trx_date,
    count() as trx_count,
    sum(amount) as trx_amount_total,
    max(amount) as trx_amount_max,
    toUInt32(uniqExact(channel)) as unique_channels,
    toUInt32(uniqExact(merchant_category_code)) as unique_mcc,
    now() as refreshed_at
from {{ ref('fact_transaction') }}
group by customer_id, trx_date
