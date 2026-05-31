{{ config(
    order_by='card_id',
    engine='ReplacingMergeTree(updated_at)'
) }}

with source as (
    select * from {{ source('bronze', 'card_cards_raw') }}
),

cleaned as (
    select
        card_id,
        account_id,
        card_pan_hash,
        nullIf(trimBoth(card_product), '') as card_product,
        expiry_date,
        nullIf(trimBoth(embossed_name), '') as embossed_name,
        nullIf(trimBoth(card_status), '') as card_status,
        issue_date,
        source_system,
        load_dttm as bronze_loaded_at
    from source
    where card_id > 0
      and account_id != ''
),

deduped as (
    select
        card_id,
        account_id,
        card_pan_hash,
        card_product,
        expiry_date,
        embossed_name,
        card_status,
        issue_date,
        source_system,
        bronze_loaded_at,
        now() as updated_at
    from cleaned
    qualify row_number() over (
        partition by card_id, source_system
        order by bronze_loaded_at desc
    ) = 1
)

select * from deduped
