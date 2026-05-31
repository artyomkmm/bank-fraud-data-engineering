from common import get_clickhouse_client


DDL_STATEMENTS = [
    """
    CREATE DATABASE IF NOT EXISTS bronze
    """,
    """
    CREATE TABLE IF NOT EXISTS bronze.crm_customers_raw (
        customer_id Int32,
        full_name String,
        phone Nullable(String),
        email Nullable(String),
        birth_date Nullable(Date32),
        city Nullable(String),
        segment Nullable(String),
        registration_date Nullable(Date),
        status Nullable(String),
        source_system LowCardinality(String) DEFAULT 'crm_db',
        load_dttm DateTime DEFAULT now()
    )
    ENGINE = MergeTree
    ORDER BY customer_id
    """,
    """
    CREATE TABLE IF NOT EXISTS bronze.core_accounts_raw (
        account_id String,
        customer_id Int32,
        product_type Nullable(String),
        currency Nullable(String),
        balance Decimal(18, 2),
        opened_date Nullable(Date),
        closed_date Nullable(Date),
        status Nullable(String),
        source_system LowCardinality(String) DEFAULT 'core_banking_db',
        load_dttm DateTime DEFAULT now()
    )
    ENGINE = MergeTree
    ORDER BY (customer_id, account_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS bronze.card_cards_raw (
        card_id Int64,
        account_id String,
        card_pan_hash Nullable(String),
        card_product Nullable(String),
        expiry_date Nullable(Date),
        embossed_name Nullable(String),
        card_status Nullable(String),
        issue_date Nullable(Date),
        source_system LowCardinality(String) DEFAULT 'card_processing_db',
        load_dttm DateTime DEFAULT now()
    )
    ENGINE = MergeTree
    ORDER BY (account_id, card_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS bronze.payments_transactions_raw (
        trx_id Int64,
        account_id String,
        customer_id Int32,
        card_id Nullable(Int64),
        trx_datetime Nullable(DateTime),
        trx_type Nullable(String),
        amount Decimal(18, 2),
        currency Nullable(String),
        channel Nullable(String),
        merchant_category_code Nullable(String),
        counterparty_name Nullable(String),
        status Nullable(String),
        posting_date Nullable(Date),
        source_system LowCardinality(String) DEFAULT 'transactions_db',
        load_dttm DateTime DEFAULT now()
    )
    ENGINE = MergeTree
    ORDER BY (customer_id, trx_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS bronze.mobile_app_sessions_raw (
        session_id String,
        customer_id Int32,
        login_time Nullable(DateTime),
        logout_time Nullable(DateTime),
        device_type Nullable(String),
        app_version Nullable(String),
        ip_address Nullable(String),
        os_version Nullable(String),
        is_new_device Bool,
        source_system LowCardinality(String) DEFAULT 'mobile_app_db',
        load_dttm DateTime DEFAULT now()
    )
    ENGINE = MergeTree
    ORDER BY (customer_id, session_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS bronze.mobile_app_events_raw (
        event_id Int64,
        session_id String,
        customer_id Int32,
        event_time Nullable(DateTime),
        event_type Nullable(String),
        event_data_raw Nullable(String),
        is_successful Bool,
        error_message Nullable(String),
        source_system LowCardinality(String) DEFAULT 'mobile_app_db',
        load_dttm DateTime DEFAULT now()
    )
    ENGINE = MergeTree
    ORDER BY (customer_id, event_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS bronze.load_state (
        mapping_name String,
        watermark_value String,
        watermark_type LowCardinality(String),
        updated_at DateTime DEFAULT now()
    )
    ENGINE = MergeTree
    ORDER BY (mapping_name, updated_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS bronze.load_audit (
        run_id String,
        mapping_name String,
        target_table String,
        load_mode LowCardinality(String),
        status LowCardinality(String),
        rows_loaded UInt64,
        last_watermark Nullable(String),
        new_watermark Nullable(String),
        started_at DateTime,
        finished_at DateTime,
        duration_ms UInt64,
        error_message Nullable(String)
    )
    ENGINE = MergeTree
    ORDER BY (mapping_name, started_at, run_id)
    """,
]


POST_DDL_STATEMENTS = [
    "ALTER TABLE bronze.crm_customers_raw MODIFY COLUMN birth_date Nullable(Date32)",
]


def main() -> None:
    client = get_clickhouse_client()
    try:
        for ddl in DDL_STATEMENTS:
            client.command(ddl)
        for ddl in POST_DDL_STATEMENTS:
            client.command(ddl)
        print("ClickHouse bronze database and tables created successfully.")
    finally:
        client.close()


if __name__ == "__main__":
    main()