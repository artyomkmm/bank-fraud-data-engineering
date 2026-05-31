{{ config(
    order_by='(layer, started_at, mapping_name)',
    materialized='view',
    tags=['gold']
) }}

with bronze_runs as (
    select
        'bronze' as layer,
        mapping_name,
        target_table,
        load_mode,
        status,
        rows_loaded,
        started_at,
        finished_at,
        duration_ms,
        error_message
    from {{ source('bronze_ops', 'load_audit') }}
),

latest_per_mapping as (
    select
        layer,
        mapping_name,
        argMax(status, started_at) as last_status,
        argMax(rows_loaded, started_at) as last_rows_loaded,
        max(started_at) as last_run_at,
        countIf(status = 'failed') as failed_runs_7d
    from bronze_runs
    where started_at >= now() - toIntervalDay(7)
    group by layer, mapping_name
)

select
    layer,
    mapping_name,
    last_status,
    last_rows_loaded,
    last_run_at,
    failed_runs_7d,
    if(last_status = 'success', 'healthy', 'degraded') as pipeline_health,
    now() as refreshed_at
from latest_per_mapping
