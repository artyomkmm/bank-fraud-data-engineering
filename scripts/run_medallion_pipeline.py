from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_step(command: list[str]) -> None:
    print("Running:", " ".join(command))
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bronze ingestion + dbt transform (Silver/Gold)")
    parser.add_argument("--full-refresh", action="store_true", help="Full refresh Bronze before transform")
    parser.add_argument("--skip-bronze", action="store_true")
    parser.add_argument("--skip-test", action="store_true")
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    python_exec = sys.executable

    run_step([python_exec, str(scripts_dir / "init_clickhouse.py")])

    if not args.skip_bronze:
        bronze_cmd = [python_exec, str(scripts_dir / "etl_to_clickhouse_bronze.py")]
        if args.full_refresh:
            bronze_cmd.append("--full-refresh")
        run_step(bronze_cmd)

    dbt_cmd = [python_exec, str(scripts_dir / "run_dbt_transform.py")]
    if args.full_refresh:
        dbt_cmd.append("--full-refresh")
    if args.skip_test:
        dbt_cmd.append("--skip-test")
    run_step(dbt_cmd)
    run_step([python_exec, str(scripts_dir / "verify_dwh.py")])

    print("Medallion pipeline completed: Bronze (ingestion) -> Silver/Gold (dbt) -> verified.")


if __name__ == "__main__":
    main()
