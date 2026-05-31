from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict

import clickhouse_connect
import psycopg2
from psycopg2.extensions import connection as PgConnection


@dataclass(frozen=True)
class PgConfig:
    host: str
    port: int
    dbname: str
    user: str = "postgres"
    password: str = "postgres"


@dataclass(frozen=True)
class ClickHouseConfig:
    host: str
    port: int
    username: str = "default"
    password: str = ""


def get_postgres_configs() -> Dict[str, PgConfig]:
    return {
        "crm": PgConfig(
            host=os.getenv("CRM_DB_HOST", "localhost"),
            port=int(os.getenv("CRM_DB_PORT", "5433")),
            dbname=os.getenv("CRM_DB_NAME", "crm_db"),
        ),
        "core": PgConfig(
            host=os.getenv("CORE_DB_HOST", "localhost"),
            port=int(os.getenv("CORE_DB_PORT", "5434")),
            dbname=os.getenv("CORE_DB_NAME", "core_banking_db"),
        ),
        "cards": PgConfig(
            host=os.getenv("CARDS_DB_HOST", "localhost"),
            port=int(os.getenv("CARDS_DB_PORT", "5435")),
            dbname=os.getenv("CARDS_DB_NAME", "card_processing_db"),
        ),
        "transactions": PgConfig(
            host=os.getenv("TRANSACTIONS_DB_HOST", "localhost"),
            port=int(os.getenv("TRANSACTIONS_DB_PORT", "5436")),
            dbname=os.getenv("TRANSACTIONS_DB_NAME", "transactions_db"),
        ),
        "mobile": PgConfig(
            host=os.getenv("MOBILE_DB_HOST", "localhost"),
            port=int(os.getenv("MOBILE_DB_PORT", "5437")),
            dbname=os.getenv("MOBILE_DB_NAME", "mobile_app_db"),
        ),
    }


def get_clickhouse_config() -> ClickHouseConfig:
    return ClickHouseConfig(
        host=os.getenv("CLICKHOUSE_HOST", "localhost"),
        port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
        username=os.getenv("CLICKHOUSE_USER", "app"),
        password=os.getenv("CLICKHOUSE_PASSWORD", "clickhouse_rbk"),
    )


def get_pg_connection(config: PgConfig) -> PgConnection:
    return psycopg2.connect(
        host=config.host,
        port=config.port,
        dbname=config.dbname,
        user=config.user,
        password=config.password,
    )


def get_clickhouse_client():
    cfg = get_clickhouse_config()
    return clickhouse_connect.get_client(
        host=cfg.host,
        port=cfg.port,
        username=cfg.username,
        password=cfg.password,
    )
