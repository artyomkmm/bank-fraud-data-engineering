# bank-fraud-data-engineering

Medallion data warehouse for bank fraud analytics: PostgreSQL sources → ClickHouse Bronze → Silver/Gold via dbt, orchestrated with Airflow.

```
PostgreSQL (5 DBs)  →  Bronze (Python ETL)  →  Silver/Gold (dbt)  →  ClickHouse
```

## Stack

| Layer | Tool | ClickHouse database |
|-------|------|---------------------|
| Bronze | Python (`scripts/etl_to_clickhouse_bronze.py`) | `bronze` |
| Silver | dbt models | `silver` |
| Gold | dbt models | `gold` |
| Reference | dbt seeds | `reference` |

**Infra:** Docker Compose (ClickHouse, 5× Postgres, Airflow)

## Prerequisites

- Docker Desktop
- Python 3.11+

## Quick start

```bash
git clone git@github.com:artyomkmm/bank-fraud-data-engineering.git
cd bank-fraud-data-engineering

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
docker compose up -d --build
```

Generate demo data and run the full pipeline:

```bash
export PYTHONPATH=scripts
export CLICKHOUSE_HOST=localhost
export CLICKHOUSE_USER=app
export CLICKHOUSE_PASSWORD=clickhouse_rbk

python scripts/generate_fake_data.py --customers 1200 --seed 42 --out-dir data
python scripts/load_sources.py --data-dir data
python scripts/run_medallion_pipeline.py --full-refresh
python scripts/verify_dwh.py
```

## Run commands

| Command | Purpose |
|---------|---------|
| `python scripts/run_medallion_pipeline.py --full-refresh` | Bronze + dbt + verify |
| `python scripts/run_dbt_transform.py` | Silver + Gold only (Bronze must exist) |
| `python scripts/run_pipeline.py` | Generate data + Bronze only |
| `python scripts/verify_dwh.py` | Health checks |

## Airflow

UI: http://localhost:8080 (`admin` / `admin`)

| DAG | Description |
|-----|-------------|
| `bank_dwh_pipeline` | Full stack: Bronze → dbt → verify |
| `bank_transform_pipeline` | dbt only (Silver + Gold) |
| `bank_bronze_pipeline` | Bronze ingestion only |

## ClickHouse

```bash
docker exec -it clickhouse_dwh clickhouse-client --user app --password clickhouse_rbk
```

```sql
SHOW DATABASES;
SELECT count() FROM bronze.crm_customers_raw;
SELECT count() FROM silver.dim_customer;
SELECT count() FROM gold.customer_360;
```

HTTP: `localhost:8123` · Native: `localhost:9000`

## Project structure

```
scripts/          Bronze ETL, pipeline runners, verify
transform/        dbt project (Silver/Gold SQL, seeds, snapshots, tests)
dags/             Airflow DAGs
sql/              Postgres source DDL
data/             Demo CSV datasets
docker-compose.yml
```

### Silver models

`dim_customer`, `dim_account`, `dim_card`, `fact_transaction`, `fact_app_session`, `fact_app_event`, `customer_scd2` (snapshot)

### Gold models

`customer_360`, `daily_transaction_summary`, `mcc_risk_enriched_transactions`, `pipeline_operations_dashboard`

## dbt (manual)

```bash
cd transform
export DBT_TARGET=local
export CLICKHOUSE_HOST=localhost
export CLICKHOUSE_USER=app
export CLICKHOUSE_PASSWORD=clickhouse_rbk

dbt deps && dbt seed && dbt run && dbt snapshot && dbt test
```
