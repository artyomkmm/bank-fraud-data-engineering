from __future__ import annotations

import argparse
from pathlib import Path

from common import get_pg_connection, get_postgres_configs

TABLE_LOAD_CONFIG = [
    ("crm", "customers", "customers.csv"),
    ("core", "accounts", "accounts.csv"),
    ("cards", "cards", "cards.csv"),
    ("transactions", "transactions", "transactions.csv"),
    ("mobile", "app_sessions", "app_sessions.csv"),
    ("mobile", "app_events", "app_events.csv"),
]


def copy_csv_to_table(table_name: str, file_path: Path, source_key: str) -> None:
    configs = get_postgres_configs()
    with get_pg_connection(configs[source_key]) as conn:
        with conn.cursor() as cur, file_path.open("r", encoding="utf-8") as f:
            cur.execute(f"TRUNCATE TABLE {table_name};")
            cur.copy_expert(
                f"COPY {table_name} FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')",
                f,
            )
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Load generated CSVs into source Postgres systems")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()

    for source_key, table_name, file_name in TABLE_LOAD_CONFIG:
        csv_path = args.data_dir / file_name
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing input file: {csv_path}")
        copy_csv_to_table(table_name, csv_path, source_key)
        print(f"Loaded {csv_path.name} -> {source_key}.{table_name}")


if __name__ == "__main__":
    main()
