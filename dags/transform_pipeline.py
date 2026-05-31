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
    dag_id="bank_transform_pipeline",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule="0 3 * * *",
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=2),
    tags=["bank", "dbt", "silver", "gold"],
) as dag:
    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"{DBT_ENV} && dbt deps --profiles-dir . --project-dir .",
    )
    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=f"{DBT_ENV} && dbt seed --profiles-dir . --project-dir .",
    )
    dbt_run_silver = BashOperator(
        task_id="dbt_run_silver",
        bash_command=f"{DBT_ENV} && dbt run --select tag:silver --profiles-dir . --project-dir .",
    )
    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot_scd2",
        bash_command=f"{DBT_ENV} && dbt snapshot --profiles-dir . --project-dir .",
    )
    dbt_test_silver = BashOperator(
        task_id="dbt_test_silver",
        bash_command=f"{DBT_ENV} && dbt test --select tag:silver --profiles-dir . --project-dir .",
    )
    dbt_run_gold = BashOperator(
        task_id="dbt_run_gold",
        bash_command=f"{DBT_ENV} && dbt run --select tag:gold --profiles-dir . --project-dir .",
    )
    dbt_test_gold = BashOperator(
        task_id="dbt_test_gold",
        bash_command=f"{DBT_ENV} && dbt test --select tag:gold --profiles-dir . --project-dir .",
    )
    verify_dwh = BashOperator(
        task_id="verify_dwh_health",
        bash_command="python /opt/project/scripts/verify_dwh.py",
    )

    dbt_deps >> dbt_seed >> dbt_run_silver >> dbt_snapshot >> dbt_test_silver >> dbt_run_gold >> dbt_test_gold >> verify_dwh
