from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from faker import Faker

fake = Faker(["ru_RU", "en_US"])


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def maybe(value, probability: float):
    return value if random.random() < probability else None


def write_csv(path: Path, rows: list[dict], headers: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def iso_date(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def iso_dt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value is not None else None


def generate_customers(count: int) -> list[dict]:
    cities = ["Almaty", "Astana", "Shymkent", "Atyrau", "Karaganda"]
    segments = ["mass", "mass", "mass", "premium", "affluent"]
    statuses = ["active", "active", "active", "inactive", "blocked"]

    rows = []
    for customer_id in range(1, count + 1):
        birth_date = fake.date_between(start_date="-60y", end_date="-18y")
        registration_date = fake.date_between(start_date="-5y", end_date="today")
        rows.append(
            {
                "customer_id": customer_id,
                "full_name": fake.name(),
                "phone": maybe(fake.msisdn()[:12], 0.92),
                "email": maybe(fake.email(), 0.88),
                "birth_date": iso_date(birth_date),
                "city": random.choice(cities),
                "segment": random.choice(segments),
                "registration_date": iso_date(registration_date),
                "status": random.choice(statuses),
            }
        )
    return rows


def generate_accounts(customers: list[dict]) -> list[dict]:
    rows = []
    seq = 100000
    product_types = ["debit", "savings", "salary", "deposit"]
    currencies = ["KZT", "KZT", "USD", "EUR"]
    statuses = ["active", "active", "active", "closed"]

    for customer in customers:
        account_count = random.randint(1, 3)
        reg_date = date.fromisoformat(customer["registration_date"])
        for _ in range(account_count):
            seq += 1
            opened_date = fake.date_between(start_date=reg_date, end_date="today")
            status = random.choice(statuses)
            closed_date = None
            if status == "closed":
                closed_date = fake.date_between(start_date=opened_date, end_date="today")
            balance = round(random.uniform(0, 1_500_000), 2)
            if status == "closed":
                balance = round(random.uniform(0, 50_000), 2)
            rows.append(
                {
                    "account_id": f"ACC{seq}",
                    "customer_id": customer["customer_id"],
                    "product_type": random.choice(product_types),
                    "currency": random.choice(currencies),
                    "balance": balance,
                    "opened_date": iso_date(opened_date),
                    "closed_date": iso_date(closed_date),
                    "status": status,
                }
            )
    return rows


def generate_cards(accounts: list[dict]) -> list[dict]:
    rows = []
    seq = 4000000000000000
    products = ["visa_classic", "visa_gold", "mastercard_standard", "mastercard_world"]
    statuses = ["active", "active", "active", "blocked", "expired"]

    for account in accounts:
        if account["status"] == "closed":
            continue
        for _ in range(random.randint(1, 2)):
            seq += 1
            issue_date = date.fromisoformat(account["opened_date"])
            expiry_date = issue_date + timedelta(days=365 * random.randint(2, 4))
            rows.append(
                {
                    "card_id": seq,
                    "account_id": account["account_id"],
                    "card_pan_hash": stable_hash(f"{seq}-masked-pan"),
                    "card_product": random.choice(products),
                    "expiry_date": iso_date(expiry_date),
                    "embossed_name": fake.name().upper(),
                    "card_status": random.choice(statuses),
                    "issue_date": iso_date(issue_date),
                }
            )
    return rows


def generate_mobile_and_transactions(
    customers: list[dict],
    accounts: list[dict],
    cards: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    sessions = []
    events = []
    transactions = []

    accounts_by_customer: dict[int, list[dict]] = defaultdict(list)
    cards_by_account: dict[str, list[dict]] = defaultdict(list)

    for account in accounts:
        accounts_by_customer[account["customer_id"]].append(account)
    for card in cards:
        cards_by_account[card["account_id"]].append(card)

    event_seq = 1
    trx_seq = 1

    for customer in customers:
        customer_id = customer["customer_id"]
        customer_accounts = [a for a in accounts_by_customer[customer_id] if a["status"] != "closed"]
        if not customer_accounts:
            continue

        known_device = None
        session_count = random.randint(2, 6)
        suspicious_session_number = random.randint(1, session_count) if random.random() < 0.18 else None

        for session_index in range(1, session_count + 1):
            login_time = fake.date_time_between(start_date="-60d", end_date="now")
            duration_minutes = random.randint(2, 18)
            logout_time = login_time + timedelta(minutes=duration_minutes)
            is_new_device = False

            if known_device is None:
                known_device = {
                    "device_type": random.choice(["android", "ios"]),
                    "app_version": random.choice(["3.7.1", "3.8.0", "3.8.2", "3.9.0"]),
                    "ip_address": fake.ipv4_public(),
                    "os_version": random.choice(["Android 13", "Android 14", "iOS 16", "iOS 17"]),
                }
                device = known_device.copy()
            elif suspicious_session_number == session_index or random.random() < 0.25:
                is_new_device = True
                device = {
                    "device_type": random.choice(["android", "ios"]),
                    "app_version": random.choice(["3.8.0", "3.8.2", "3.9.0"]),
                    "ip_address": fake.ipv4_public(),
                    "os_version": random.choice(["Android 14", "iOS 17"]),
                }
            else:
                device = known_device.copy()

            session_id = uuid4().hex[:32]
            sessions.append(
                {
                    "session_id": session_id,
                    "customer_id": customer_id,
                    "login_time": iso_dt(login_time),
                    "logout_time": iso_dt(logout_time),
                    "device_type": device["device_type"],
                    "app_version": device["app_version"],
                    "ip_address": device["ip_address"],
                    "os_version": device["os_version"],
                    "is_new_device": str(is_new_device).lower(),
                }
            )

            failed_login_count = random.randint(0, 4 if is_new_device else 2)
            cursor_time = login_time - timedelta(minutes=1)
            for _ in range(failed_login_count):
                cursor_time += timedelta(seconds=random.randint(10, 35))
                events.append(
                    {
                        "event_id": event_seq,
                        "session_id": session_id,
                        "customer_id": customer_id,
                        "event_time": iso_dt(cursor_time),
                        "event_type": "login_failed",
                        "event_data": json.dumps({"reason": random.choice(["wrong_password", "otp_failed", "biometric_failed"])}, ensure_ascii=False),
                        "is_successful": "false",
                        "error_message": random.choice(["Wrong password", "OTP mismatch", "Biometric rejected"]),
                    }
                )
                event_seq += 1

            cursor_time = login_time
            events.append(
                {
                    "event_id": event_seq,
                    "session_id": session_id,
                    "customer_id": customer_id,
                    "event_time": iso_dt(cursor_time),
                    "event_type": "login",
                    "event_data": json.dumps({"method": random.choice(["password", "biometric", "otp"]), "is_new_device": is_new_device}, ensure_ascii=False),
                    "is_successful": "true",
                    "error_message": None,
                }
            )
            event_seq += 1

            event_types = ["view_balance", "view_cards", "change_limits", "add_beneficiary", "make_transfer"]
            event_count = random.randint(2, 6)

            for _ in range(event_count):
                cursor_time += timedelta(seconds=random.randint(20, 90))
                event_type = random.choice(event_types)
                is_successful = random.random() > (0.22 if is_new_device and event_type == "make_transfer" else 0.06)

                events.append(
                    {
                        "event_id": event_seq,
                        "session_id": session_id,
                        "customer_id": customer_id,
                        "event_time": iso_dt(cursor_time),
                        "event_type": event_type,
                        "event_data": json.dumps({"screen": random.choice(["home", "cards", "payments", "profile"]), "session_no": session_index}, ensure_ascii=False),
                        "is_successful": str(is_successful).lower(),
                        "error_message": None if is_successful else "Operation declined",
                    }
                )
                current_event_id = event_seq
                event_seq += 1

                if event_type == "make_transfer" and is_successful:
                    account = random.choice(customer_accounts)
                    account_cards = cards_by_account.get(account["account_id"], [])
                    card_id = random.choice(account_cards)["card_id"] if account_cards else None

                    if is_new_device and (failed_login_count >= 2 or random.random() < 0.65):
                        amount = round(random.uniform(120_000, 500_000), 2)
                    else:
                        amount = round(random.uniform(1_000, 90_000), 2)

                    transactions.append(
                        {
                            "trx_id": trx_seq,
                            "account_id": account["account_id"],
                            "customer_id": customer_id,
                            "card_id": card_id,
                            "trx_datetime": iso_dt(cursor_time + timedelta(seconds=20)),
                            "trx_type": "debit",
                            "amount": amount,
                            "currency": account["currency"],
                            "channel": random.choice(["mobile", "p2p", "web"]),
                            "merchant_category_code": random.choice(["6012", "4829", "5411", "5999"]),
                            "counterparty_name": random.choice(["TRANSFER", "PAYMENT", fake.company()[:90]]),
                            "status": "posted",
                            "posting_date": iso_date((cursor_time + timedelta(seconds=20)).date()),
                        }
                    )
                    trx_seq += 1

            additional_trx_count = random.randint(1, 4)
            for _ in range(additional_trx_count):
                account = random.choice(customer_accounts)
                account_cards = cards_by_account.get(account["account_id"], [])
                card_id = random.choice(account_cards)["card_id"] if account_cards else None
                trx_time = fake.date_time_between(start_date=login_time - timedelta(days=25), end_date=logout_time + timedelta(days=3))
                trx_type = random.choice(["debit", "debit", "credit"])
                amount = round(random.uniform(500, 150_000), 2)
                transactions.append(
                    {
                        "trx_id": trx_seq,
                        "account_id": account["account_id"],
                        "customer_id": customer_id,
                        "card_id": card_id,
                        "trx_datetime": iso_dt(trx_time),
                        "trx_type": trx_type,
                        "amount": amount,
                        "currency": account["currency"],
                        "channel": random.choice(["atm", "pos", "mobile", "web"]),
                        "merchant_category_code": random.choice(["5411", "5541", "6011", "5732", "4900"]),
                        "counterparty_name": random.choice([fake.company()[:90], "ATM CASHOUT", "GROCERY", "UTILITY PAYMENT"]),
                        "status": random.choice(["posted", "posted", "pending"]),
                        "posting_date": iso_date(trx_time.date()),
                    }
                )
                trx_seq += 1

    return sessions, events, transactions


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate fake banking data for source systems")
    parser.add_argument("--customers", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", type=Path, default=Path("data"))
    args = parser.parse_args()

    random.seed(args.seed)
    Faker.seed(args.seed)

    customers = generate_customers(args.customers)
    accounts = generate_accounts(customers)
    cards = generate_cards(accounts)
    sessions, events, transactions = generate_mobile_and_transactions(customers, accounts, cards)

    write_csv(
        args.out_dir / "customers.csv",
        customers,
        ["customer_id", "full_name", "phone", "email", "birth_date", "city", "segment", "registration_date", "status"],
    )
    write_csv(
        args.out_dir / "accounts.csv",
        accounts,
        ["account_id", "customer_id", "product_type", "currency", "balance", "opened_date", "closed_date", "status"],
    )
    write_csv(
        args.out_dir / "cards.csv",
        cards,
        ["card_id", "account_id", "card_pan_hash", "card_product", "expiry_date", "embossed_name", "card_status", "issue_date"],
    )
    write_csv(
        args.out_dir / "transactions.csv",
        transactions,
        ["trx_id", "account_id", "customer_id", "card_id", "trx_datetime", "trx_type", "amount", "currency", "channel", "merchant_category_code", "counterparty_name", "status", "posting_date"],
    )
    write_csv(
        args.out_dir / "app_sessions.csv",
        sessions,
        ["session_id", "customer_id", "login_time", "logout_time", "device_type", "app_version", "ip_address", "os_version", "is_new_device"],
    )
    write_csv(
        args.out_dir / "app_events.csv",
        events,
        ["event_id", "session_id", "customer_id", "event_time", "event_type", "event_data", "is_successful", "error_message"],
    )

    print(f"Generated data into: {args.out_dir.resolve()}")
    print(f"customers={len(customers)} accounts={len(accounts)} cards={len(cards)} sessions={len(sessions)} events={len(events)} transactions={len(transactions)}")


if __name__ == "__main__":
    main()
