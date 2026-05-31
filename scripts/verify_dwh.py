from __future__ import annotations

import sys

from common import get_clickhouse_client

CHECKS = [
    ("bronze.crm_customers_raw", "select count() > 0 from bronze.crm_customers_raw"),
    ("silver.dim_customer", "select count() > 0 from silver.dim_customer"),
    ("gold.customer_360", "select count() > 0 from gold.customer_360"),
    (
        "PII hashing",
        """
        select count() = 0
        from silver.dim_customer
        where (phone_hash is not null and length(phone_hash) != 64)
           or (email_hash is not null and length(email_hash) != 64)
        """,
    ),
    (
        "bronze audit healthy",
        """
        select count() = 0
        from (
            select mapping_name, argMax(status, started_at) as last_status
            from bronze.load_audit
            group by mapping_name
        )
        where last_status = 'failed'
        """,
    ),
]


def main() -> None:
    client = get_clickhouse_client()
    failed = 0
    try:
        print("RBK DWH verification")
        print("-" * 50)
        for name, sql in CHECKS:
            try:
                result = client.query(sql)
                ok = bool(result.result_rows[0][0])
                status = "PASS" if ok else "FAIL"
                print(f"[{status}] {name}")
                if not ok:
                    failed += 1
            except Exception as exc:
                print(f"[FAIL] {name}: {exc}")
                failed += 1
        print("-" * 50)
        if failed:
            print(f"Verification failed: {failed} check(s)")
            sys.exit(1)
        print("All checks passed.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
