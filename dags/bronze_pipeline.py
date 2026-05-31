from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "data-platform",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="bank_bronze_pipeline",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule="0 2 * * *",
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=2),
    tags=["bank", "bronze", "clickhouse"],
) as dag:
    init_clickhouse = BashOperator(
        task_id="init_clickhouse",
        bash_command="python /opt/project/scripts/init_clickhouse.py",
    )

    load_crm_customers = BashOperator(
        task_id="load_crm_customers",
        bash_command="python /opt/project/scripts/etl_to_clickhouse_bronze.py --mapping crm_customers",
    )

    load_core_accounts = BashOperator(
        task_id="load_core_accounts",
        bash_command="python /opt/project/scripts/etl_to_clickhouse_bronze.py --mapping core_accounts",
    )

    load_cards = BashOperator(
        task_id="load_cards",
        bash_command="python /opt/project/scripts/etl_to_clickhouse_bronze.py --mapping cards",
    )

    load_transactions = BashOperator(
        task_id="load_transactions",
        bash_command="python /opt/project/scripts/etl_to_clickhouse_bronze.py --mapping transactions",
    )

    load_mobile_sessions = BashOperator(
        task_id="load_mobile_sessions",
        bash_command="python /opt/project/scripts/etl_to_clickhouse_bronze.py --mapping mobile_sessions",
    )

    load_mobile_events = BashOperator(
        task_id="load_mobile_events",
        bash_command="python /opt/project/scripts/etl_to_clickhouse_bronze.py --mapping mobile_events",
    )

    init_clickhouse >> [
        load_crm_customers,
        load_core_accounts,
        load_cards,
        load_transactions,
        load_mobile_sessions,
        load_mobile_events,
    ]
