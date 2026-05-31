from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> None:
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True, env=os.environ.copy())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run dbt transformations (Silver + Gold)")
    parser.add_argument("--select", default=None, help="dbt selection, e.g. tag:silver or gold.customer_360")
    parser.add_argument("--full-refresh", action="store_true")
    parser.add_argument("--skip-test", action="store_true")
    parser.add_argument("--deps-only", action="store_true")
    args = parser.parse_args()

    transform_dir = Path(__file__).resolve().parent.parent / "transform"
    if not transform_dir.exists():
        raise FileNotFoundError(f"dbt project not found: {transform_dir}")

    os.environ.setdefault("DBT_TARGET", "local")
    os.environ.setdefault("CLICKHOUSE_HOST", "localhost")
    os.environ.setdefault("CLICKHOUSE_PORT", "8123")
    os.environ.setdefault("CLICKHOUSE_USER", "app")
    os.environ.setdefault("CLICKHOUSE_PASSWORD", "clickhouse_rbk")

    run(["dbt", "deps", "--profiles-dir", ".", "--project-dir", "."], transform_dir)
    if args.deps_only:
        return

    run(["dbt", "seed", "--profiles-dir", ".", "--project-dir", "."], transform_dir)

    run_cmd = ["dbt", "run", "--profiles-dir", ".", "--project-dir", "."]
    if args.select:
        run_cmd.extend(["--select", args.select])
    if args.full_refresh:
        run_cmd.append("--full-refresh")
    run(run_cmd, transform_dir)
    run(["dbt", "snapshot", "--profiles-dir", ".", "--project-dir", "."], transform_dir)

    if not args.skip_test:
        test_cmd = ["dbt", "test", "--profiles-dir", ".", "--project-dir", "."]
        if args.select:
            test_cmd.extend(["--select", args.select])
        run(test_cmd, transform_dir)

    print("dbt transform completed successfully.")


if __name__ == "__main__":
    main()
