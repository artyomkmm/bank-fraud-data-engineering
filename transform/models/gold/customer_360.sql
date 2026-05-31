{{ config(
    order_by='customer_id',
    engine='ReplacingMergeTree(refreshed_at)'
) }}

with customers as (
    select * from {{ ref('dim_customer') }}
),

customer_accounts as (
    select
        acc.customer_id as customer_id,
        count() as account_count,
        sum(acc.balance) as total_balance,
        uniqExact(card.card_id) as card_count
    from {{ ref('dim_account') }} as acc
    left join {{ ref('dim_card') }} as card on card.account_id = acc.account_id
    group by acc.customer_id
),

transactions as (
    select
        customer_id,
        count() as trx_count,
        sum(amount) as trx_amount_total,
        max(amount) as trx_amount_max,
        max(trx_datetime) as last_trx_datetime
    from {{ ref('fact_transaction') }}
    group by customer_id
),

sessions as (
    select
        customer_id,
        count() as session_count,
        max(login_time) as last_login_time,
        countIf(is_new_device) as new_device_session_count
    from {{ ref('fact_app_session') }}
    group by customer_id
),

events as (
    select
        customer_id,
        countIf(is_successful = false) as failed_event_count
    from {{ ref('fact_app_event') }}
    group by customer_id
),

metrics_union as (
    select
        customer_id,
        account_count,
        total_balance,
        card_count,
        toUInt64(0) as trx_count,
        toDecimal64(0, 2) as trx_amount_total,
        toDecimal64(0, 2) as trx_amount_max,
        cast(null as Nullable(DateTime)) as last_trx_datetime,
        toUInt64(0) as session_count,
        cast(null as Nullable(DateTime)) as last_login_time,
        toUInt64(0) as new_device_session_count,
        toUInt64(0) as failed_event_count
    from customer_accounts

    union all

    select
        customer_id,
        toUInt64(0) as account_count,
        toDecimal64(0, 2) as total_balance,
        toUInt64(0) as card_count,
        trx_count,
        trx_amount_total,
        trx_amount_max,
        last_trx_datetime,
        toUInt64(0) as session_count,
        cast(null as Nullable(DateTime)) as last_login_time,
        toUInt64(0) as new_device_session_count,
        toUInt64(0) as failed_event_count
    from transactions

    union all

    select
        customer_id,
        toUInt64(0),
        toDecimal64(0, 2),
        toUInt64(0),
        toUInt64(0),
        toDecimal64(0, 2),
        toDecimal64(0, 2),
        cast(null as Nullable(DateTime)),
        session_count,
        last_login_time,
        new_device_session_count,
        toUInt64(0)
    from sessions

    union all

    select
        customer_id,
        toUInt64(0),
        toDecimal64(0, 2),
        toUInt64(0),
        toUInt64(0),
        toDecimal64(0, 2),
        toDecimal64(0, 2),
        cast(null as Nullable(DateTime)),
        toUInt64(0),
        cast(null as Nullable(DateTime)),
        toUInt64(0),
        failed_event_count
    from events
),

metrics as (
    select
        customer_id,
        max(account_count) as account_count,
        max(total_balance) as total_balance,
        max(card_count) as card_count,
        max(trx_count) as trx_count,
        max(trx_amount_total) as trx_amount_total,
        max(trx_amount_max) as trx_amount_max,
        max(last_trx_datetime) as last_trx_datetime,
        max(session_count) as session_count,
        max(last_login_time) as last_login_time,
        max(new_device_session_count) as new_device_session_count,
        max(failed_event_count) as failed_event_count
    from metrics_union
    group by customer_id
)

select
    c.customer_id,
    c.full_name,
    c.segment,
    c.city,
    c.status,
    toUInt32(coalesce(m.account_count, 0)) as account_count,
    toUInt32(coalesce(m.card_count, 0)) as card_count,
    coalesce(m.total_balance, 0) as total_balance,
    toUInt64(coalesce(m.trx_count, 0)) as trx_count,
    coalesce(m.trx_amount_total, 0) as trx_amount_total,
    coalesce(m.trx_amount_max, 0) as trx_amount_max,
    m.last_trx_datetime,
    toUInt64(coalesce(m.session_count, 0)) as session_count,
    m.last_login_time,
    toUInt64(coalesce(m.new_device_session_count, 0)) as new_device_session_count,
    toUInt64(coalesce(m.failed_event_count, 0)) as failed_event_count,
    now() as refreshed_at
from customers as c
left join metrics as m on m.customer_id = c.customer_id
