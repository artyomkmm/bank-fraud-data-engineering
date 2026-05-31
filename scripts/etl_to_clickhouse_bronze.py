from __future__ import annotations

import argparse
from datetime import date, datetime
from decimal import Decimal
from time import perf_counter
from typing import Any, Iterable, List, Sequence
from uuid import uuid4

from common import get_clickhouse_client, get_pg_connection, get_postgres_configs
from init_clickhouse import DDL_STATEMENTS

SOURCE_TO_BRONZE = [
    {
        "mapping_name": "crm_customers",
        "source_key": "crm",
        "select_columns_sql": "customer_id, full_name, phone, email, birth_date, city, segment, registration_date, status",
        "source_table": "customers",
        "order_by_sql": "customer_id",
        "target_table": "bronze.crm_customers_raw",
        "target_columns": [
            "customer_id", "full_name", "phone", "email", "birth_date", "city", "segment", "registration_date", "status"
        ],
        "incremental_column": "customer_id",
        "incremental_type": "int",
        "incremental_value_idx": 0,
    },
    {
        "mapping_name": "core_accounts",
        "source_key": "core",
        "select_columns_sql": "account_id, customer_id, product_type, currency, balance, opened_date, closed_date, status",
        "source_table": "accounts",
        "order_by_sql": "account_id",
        "target_table": "bronze.core_accounts_raw",
        "target_columns": [
            "account_id", "customer_id", "product_type", "currency", "balance", "opened_date", "closed_date", "status"
        ],
        "incremental_column": "account_id",
        "incremental_type": "str",
        "incremental_value_idx": 0,
    },
    {
        "mapping_name": "cards",
        "source_key": "cards",
        "select_columns_sql": "card_id, account_id, card_pan_hash, card_product, expiry_date, embossed_name, card_status, issue_date",
        "source_table": "cards",
        "order_by_sql": "card_id",
        "target_table": "bronze.card_cards_raw",
        "target_columns": [
            "card_id", "account_id", "card_pan_hash", "card_product", "expiry_date", "embossed_name", "card_status", "issue_date"
        ],
        "incremental_column": "card_id",
        "incremental_type": "int",
        "incremental_value_idx": 0,
    },
    {
        "mapping_name": "transactions",
        "source_key": "transactions",
        "select_columns_sql": (
            "trx_id, account_id, customer_id, card_id, trx_datetime, trx_type, amount, currency, channel, "
            "merchant_category_code, counterparty_name, status, posting_date"
        ),
        "source_table": "transactions",
        "order_by_sql": "trx_id",
        "target_table": "bronze.payments_transactions_raw",
        "target_columns": [
            "trx_id", "account_id", "customer_id", "card_id", "trx_datetime", "trx_type", "amount", "currency",
            "channel", "merchant_category_code", "counterparty_name", "status", "posting_date"
        ],
        "incremental_column": "trx_id",
        "incremental_type": "int",
        "incremental_value_idx": 0,
    },
    {
        "mapping_name": "mobile_sessions",
        "source_key": "mobile",
        "select_columns_sql": "session_id, customer_id, login_time, logout_time, device_type, app_version, ip_address, os_version, is_new_device",
        "source_table": "app_sessions",
        "order_by_sql": "session_id",
        "target_table": "bronze.mobile_app_sessions_raw",
        "target_columns": [
            "session_id", "customer_id", "login_time", "logout_time", "device_type", "app_version", "ip_address",
            "os_version", "is_new_device"
        ],
        "incremental_column": "session_id",
        "incremental_type": "str",
        "incremental_value_idx": 0,
    },
    {
        "mapping_name": "mobile_events",
        "source_key": "mobile",
        "select_columns_sql": "event_id, session_id, customer_id, event_time, event_type, event_data::text AS event_data_raw, is_successful, error_message",
        "source_table": "app_events",
        "order_by_sql": "event_id",
        "target_table": "bronze.mobile_app_events_raw",
        "target_columns": [
            "event_id", "session_id", "customer_id", "event_time", "event_type", "event_data_raw", "is_successful", "error_message"
        ],
        "incremental_column": "event_id",
        "incremental_type": "int",
        "incremental_value_idx": 0,
    },
]

BRONZE_TABLES = [item["target_table"] for item in SOURCE_TO_BRONZE]
MAPPINGS_BY_NAME = {item["mapping_name"]: item for item in SOURCE_TO_BRONZE}
MAPPINGS_BY_TABLE = {item["target_table"]: item for item in SOURCE_TO_BRONZE}


def ensure_clickhouse_ready(client) -> None:
    for ddl in DDL_STATEMENTS:
        client.command(ddl)


def truncate_bronze(client) -> None:
    for table_name in BRONZE_TABLES:
        client.command(f"TRUNCATE TABLE {table_name}")


def truncate_target_table(client, table_name: str) -> None:
    client.command(f"TRUNCATE TABLE {table_name}")


def parse_watermark(raw_value: str, value_type: str) -> Any:
    if value_type == "int":
        return int(raw_value)
    if value_type == "datetime":
        return datetime.fromisoformat(raw_value)
    return raw_value


def serialize_watermark(value: Any, value_type: str) -> str:
    if value_type == "datetime":
        return value.isoformat(sep=" ")
    return str(value)


def get_last_watermark(client, mapping_name: str, value_type: str) -> Any | None:
    result = client.query(
        f"""
        SELECT watermark_value
        FROM bronze.load_state
        WHERE mapping_name = '{mapping_name}'
        ORDER BY updated_at DESC
        LIMIT 1
        """
    )
    if not result.result_rows:
        return None
    return parse_watermark(result.result_rows[0][0], value_type)


def write_watermark(client, mapping_name: str, value_type: str, watermark_value: Any) -> None:
    client.insert(
        "bronze.load_state",
        [[mapping_name, serialize_watermark(watermark_value, value_type), value_type]],
        column_names=["mapping_name", "watermark_value", "watermark_type"],
    )


def write_audit_row(
    client,
    run_id: str,
    mapping_name: str,
    target_table: str,
    load_mode: str,
    status: str,
    rows_loaded: int,
    started_at: datetime,
    finished_at: datetime,
    duration_ms: int,
    last_watermark: Any | None,
    new_watermark: Any | None,
    watermark_type: str,
    error_message: str | None = None,
) -> None:
    serialized_last = serialize_watermark(last_watermark, watermark_type) if last_watermark is not None else None
    serialized_new = serialize_watermark(new_watermark, watermark_type) if new_watermark is not None else None
    client.insert(
        "bronze.load_audit",
        [[
            run_id,
            mapping_name,
            target_table,
            load_mode,
            status,
            rows_loaded,
            serialized_last,
            serialized_new,
            started_at,
            finished_at,
            duration_ms,
            error_message,
        ]],
        column_names=[
            "run_id",
            "mapping_name",
            "target_table",
            "load_mode",
            "status",
            "rows_loaded",
            "last_watermark",
            "new_watermark",
            "started_at",
            "finished_at",
            "duration_ms",
            "error_message",
        ],
    )


def build_select_sql(mapping: dict, use_incremental: bool) -> str:
    where_clause = ""
    if use_incremental:
        where_clause = f"WHERE {mapping['incremental_column']} > %s"
    return (
        f"SELECT {mapping['select_columns_sql']} "
        f"FROM {mapping['source_table']} "
        f"{where_clause} "
        f"ORDER BY {mapping['order_by_sql']}"
    )


def normalize_row(row: Sequence[Any]) -> list[Any]:
    normalized = []
    for value in row:
        if isinstance(value, Decimal):
            normalized.append(value)
        elif isinstance(value, (datetime, date)):
            normalized.append(value)
        else:
            normalized.append(value)
    return normalized


def fetch_in_chunks(cursor, size: int) -> Iterable[List[Sequence[Any]]]:
    while True:
        rows = cursor.fetchmany(size)
        if not rows:
            break
        yield rows


def load_one_mapping(mapping: dict, chunk_size: int, print_samples: bool, replace_table: bool) -> None:
    pg_config = get_postgres_configs()[mapping["source_key"]]
    client = get_clickhouse_client()
    run_id = str(uuid4())
    load_mode = "full_refresh" if replace_table else "incremental"
    start_dt = datetime.now()
    start_ts = perf_counter()
    total_rows = 0
    last_watermark = None
    new_max_watermark = None
    try:
        ensure_clickhouse_ready(client)
        if replace_table:
            truncate_target_table(client, mapping["target_table"])
        last_watermark = None if replace_table else get_last_watermark(
            client,
            mapping["mapping_name"],
            mapping["incremental_type"],
        )
        new_max_watermark = last_watermark
        with get_pg_connection(pg_config) as conn:
            with conn.cursor() as cur:
                select_sql = build_select_sql(mapping, last_watermark is not None)
                if last_watermark is None:
                    cur.execute(select_sql)
                else:
                    cur.execute(select_sql, (last_watermark,))
                first_chunk = True
                for chunk in fetch_in_chunks(cur, chunk_size):
                    values = [normalize_row(row) for row in chunk]
                    client.insert(mapping["target_table"], values, column_names=mapping["target_columns"])
                    total_rows += len(values)
                    idx = mapping["incremental_value_idx"]
                    chunk_watermarks = [row[idx] for row in chunk if row[idx] is not None]
                    if chunk_watermarks:
                        chunk_max = max(chunk_watermarks)
                        if new_max_watermark is None or chunk_max > new_max_watermark:
                            new_max_watermark = chunk_max
                    if print_samples and first_chunk and values:
                        print(f"Sample from {mapping['target_table']}: {values[0]}")
                        first_chunk = False
        if new_max_watermark is not None and new_max_watermark != last_watermark:
            write_watermark(
                client,
                mapping["mapping_name"],
                mapping["incremental_type"],
                new_max_watermark,
            )
        end_dt = datetime.now()
        duration_ms = int((perf_counter() - start_ts) * 1000)
        write_audit_row(
            client=client,
            run_id=run_id,
            mapping_name=mapping["mapping_name"],
            target_table=mapping["target_table"],
            load_mode=load_mode,
            status="success",
            rows_loaded=total_rows,
            started_at=start_dt,
            finished_at=end_dt,
            duration_ms=duration_ms,
            last_watermark=last_watermark,
            new_watermark=new_max_watermark,
            watermark_type=mapping["incremental_type"],
            error_message=None,
        )
        print(f"Loaded {total_rows} rows into {mapping['target_table']}")
    except Exception as exc:
        end_dt = datetime.now()
        duration_ms = int((perf_counter() - start_ts) * 1000)
        try:
            write_audit_row(
                client=client,
                run_id=run_id,
                mapping_name=mapping["mapping_name"],
                target_table=mapping["target_table"],
                load_mode=load_mode,
                status="failed",
                rows_loaded=total_rows,
                started_at=start_dt,
                finished_at=end_dt,
                duration_ms=duration_ms,
                last_watermark=last_watermark,
                new_watermark=new_max_watermark,
                watermark_type=mapping["incremental_type"],
                error_message=str(exc)[:1000],
            )
        finally:
            raise
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Move data from source Postgres DBs into ClickHouse bronze")
    parser.add_argument("--chunk-size", type=int, default=2000)
    parser.add_argument("--print-samples", action="store_true")
    parser.add_argument(
        "--mapping",
        action="append",
        default=[],
        help="Load one or many mappings by mapping_name or target table (repeatable)",
    )
    parser.add_argument(
        "--replace-table",
        action="store_true",
        help="Truncate each selected target table before loading it",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Truncate all selected target tables before loading (default is incremental)",
    )
    args = parser.parse_args()

    selected_mappings = SOURCE_TO_BRONZE
    if args.mapping:
        selected_mappings = []
        for key in args.mapping:
            mapping = MAPPINGS_BY_NAME.get(key) or MAPPINGS_BY_TABLE.get(key)
            if mapping is None:
                valid = sorted(set([*MAPPINGS_BY_NAME.keys(), *MAPPINGS_BY_TABLE.keys()]))
                raise ValueError(f"Unknown mapping: {key}. Valid values: {', '.join(valid)}")
            selected_mappings.append(mapping)

    client = get_clickhouse_client()
    try:
        ensure_clickhouse_ready(client)
        if args.full_refresh and not args.mapping:
            truncate_bronze(client)
        elif args.full_refresh and args.mapping:
            for mapping in selected_mappings:
                truncate_target_table(client, mapping["target_table"])
    finally:
        client.close()

    effective_replace_table = args.replace_table or args.full_refresh
    for mapping in selected_mappings:
        load_one_mapping(mapping, args.chunk_size, args.print_samples, effective_replace_table)


if __name__ == "__main__":
    main()
