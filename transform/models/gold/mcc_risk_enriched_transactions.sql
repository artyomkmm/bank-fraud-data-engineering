{{ config(
    order_by='(trx_date, customer_id, trx_id)',
    engine='ReplacingMergeTree(refreshed_at)',
    partition_by='toYYYYMM(assumeNotNull(trx_date))',
    tags=['gold']
) }}

select
    t.trx_id,
    t.customer_id,
    t.trx_date,
    t.trx_datetime,
    t.amount,
    t.currency,
    t.channel,
    t.merchant_category_code,
    coalesce(m.mcc_category, 'Unknown') as mcc_category,
    coalesce(m.risk_weight, 30) as mcc_risk_weight,
    t.amount * (coalesce(m.risk_weight, 30) / 100.0) as risk_weighted_amount,
    now() as refreshed_at
from {{ ref('fact_transaction') }} as t
left join {{ ref('risk_mcc_codes') }} as m on toString(m.mcc_code) = t.merchant_category_code
