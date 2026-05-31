from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

DBT_ENV = (
    "export DBT_TARGET=docker && "
    "export CLICKHOUSE_HOST=clickhouse_dwh && "
    "export CLICKHOUSE_PORT=8123 && "
    "export CLICKHOUSE_USER=app && "
    "export CLICKHOUSE_PASSWORD=clickhouse_rbk && "
    "cd /opt/project/transform"
)

default_args = {
    "owner": "data-platform",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="bank_dwh_pipeline",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule="0 2 * * *",
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=4),
    tags=["bank", "dwh", "bronze", "dbt"],
) as dag:
    init_bronze = BashOperator(
        task_id="init_bronze",
        bash_command="python /opt/project/scripts/init_clickhouse.py",
    )

    load_crm = BashOperator(
        task_id="bronze_load_crm_customers",
        bash_command="python /opt/project/scripts/etl_to_clickhouse_bronze.py --mapping crm_customers",
    )
    load_core = BashOperator(
        task_id="bronze_load_core_accounts",
        bash_command="python /opt/project/scripts/etl_to_clickhouse_bronze.py --mapping core_accounts",
    )
    load_cards = BashOperator(
        task_id="bronze_load_cards",
        bash_command="python /opt/project/scripts/etl_to_clickhouse_bronze.py --mapping cards",
    )
    load_trx = BashOperator(
        task_id="bronze_load_transactions",
        bash_command="python /opt/project/scripts/etl_to_clickhouse_bronze.py --mapping transactions",
    )
    load_sessions = BashOperator(
        task_id="bronze_load_mobile_sessions",
        bash_command="python /opt/project/scripts/etl_to_clickhouse_bronze.py --mapping mobile_sessions",
    )
    load_events = BashOperator(
        task_id="bronze_load_mobile_events",
        bash_command="python /opt/project/scripts/etl_to_clickhouse_bronze.py --mapping mobile_events",
    )

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"{DBT_ENV} && dbt deps --profiles-dir . --project-dir .",
    )
    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=f"{DBT_ENV} && dbt seed --profiles-dir . --project-dir .",
    )
    dbt_run = BashOperator(
        task_id="dbt_run_all",
        bash_command=f"{DBT_ENV} && dbt run --profiles-dir . --project-dir .",
    )
    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot_scd2",
        bash_command=f"{DBT_ENV} && dbt snapshot --profiles-dir . --project-dir .",
    )
    dbt_test = BashOperator(
        task_id="dbt_test_all",
        bash_command=f"{DBT_ENV} && dbt test --profiles-dir . --project-dir .",
    )
    verify_dwh = BashOperator(
        task_id="verify_dwh_health",
        bash_command="python /opt/project/scripts/verify_dwh.py",
    )

    bronze_loads = [load_crm, load_core, load_cards, load_trx, load_sessions, load_events]

    init_bronze >> bronze_loads >> dbt_deps >> dbt_seed >> dbt_run >> dbt_snapshot
    dbt_snapshot >> dbt_test >> verify_dwh
