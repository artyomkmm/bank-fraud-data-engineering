{{ config(
    order_by='(event_date, customer_id, event_id)',
    engine='ReplacingMergeTree(updated_at)',
    partition_by='toYYYYMM(event_date)'
) }}

with source as (
    select * from {{ source('bronze', 'mobile_app_events_raw') }}
),

cleaned as (
    select
        event_id,
        session_id,
        customer_id,
        event_time,
        assumeNotNull(toDate(coalesce(event_time, load_dttm))) as event_date,
        nullIf(trimBoth(event_type), '') as event_type,
        event_data_raw,
        is_successful,
        nullIf(trimBoth(error_message), '') as error_message,
        source_system,
        load_dttm as bronze_loaded_at
    from source
    where event_id > 0
      and session_id != ''
      and customer_id > 0
),

deduped as (
    select
        event_id,
        session_id,
        customer_id,
        event_time,
        event_date,
        event_type,
        event_data_raw,
        is_successful,
        error_message,
        source_system,
        bronze_loaded_at,
        now() as updated_at
    from cleaned
    qualify row_number() over (
        partition by event_id, source_system
        order by bronze_loaded_at desc
    ) = 1
)

select * from deduped
