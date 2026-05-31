{{ config(
    order_by='(session_date, customer_id, session_id)',
    engine='ReplacingMergeTree(updated_at)',
    partition_by='toYYYYMM(session_date)'
) }}

with source as (
    select * from {{ source('bronze', 'mobile_app_sessions_raw') }}
),

cleaned as (
    select
        session_id,
        customer_id,
        login_time,
        logout_time,
        assumeNotNull(toDate(coalesce(login_time, load_dttm))) as session_date,
        nullIf(trimBoth(device_type), '') as device_type,
        nullIf(trimBoth(app_version), '') as app_version,
        nullIf(trimBoth(ip_address), '') as ip_address,
        nullIf(trimBoth(os_version), '') as os_version,
        is_new_device,
        source_system,
        load_dttm as bronze_loaded_at
    from source
    where session_id != ''
      and customer_id > 0
),

deduped as (
    select
        session_id,
        customer_id,
        login_time,
        logout_time,
        session_date,
        device_type,
        app_version,
        ip_address,
        os_version,
        is_new_device,
        source_system,
        bronze_loaded_at,
        now() as updated_at
    from cleaned
    qualify row_number() over (
        partition by session_id, source_system
        order by bronze_loaded_at desc
    ) = 1
)

select * from deduped
