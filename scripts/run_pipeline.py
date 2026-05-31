from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_step(command: list[str]) -> None:
    print("Running:", " ".join(command))
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full Bronze-only pipeline")
    parser.add_argument("--customers", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--print-samples", action="store_true")
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    python_exec = sys.executable

    run_step([
        python_exec,
        str(scripts_dir / "generate_fake_data.py"),
        "--customers",
        str(args.customers),
        "--seed",
        str(args.seed),
        "--out-dir",
        str(scripts_dir.parent / "data"),
    ])
    run_step([
        python_exec,
        str(scripts_dir / "load_sources.py"),
        "--data-dir",
        str(scripts_dir.parent / "data"),
    ])
    run_step([python_exec, str(scripts_dir / "init_clickhouse.py")])

    etl_command = [python_exec, str(scripts_dir / "etl_to_clickhouse_bronze.py")]
    if args.print_samples:
        etl_command.append("--print-samples")
    run_step(etl_command)


if __name__ == "__main__":
    main()
