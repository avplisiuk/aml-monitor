"""Synthetic transaction generator for AML monitoring."""

import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from faker import Faker
import pandas as pd
import uuid

fake = Faker()
Faker.seed(42)
random.seed(42)

COUNTRIES_HIGH_RISK = [
    "AF", "IQ", "KP", "SY", "VN", "YE", "IR", "LY", "PK", "MM",
    "NG", "SD", "SO", "SS", "ZW",
]

COUNTRIES_SANCTIONED = ["KP", "IR", "SY", "CU", "VE", "RU", "BY"]

PAYMENT_METHODS = ["wire", "swift", "cash_deposit", "crypto", "card", "sepa"]
WIRE_TYPES = ["domestic", "cross_border"]


def generate_client_id():
    return f"C{random.randint(100000, 999999)}"


def generate_account():
    return {
        "account_id": f"ACC{random.randint(10000000, 99999999)}",
        "client_id": generate_client_id(),
        "country": fake.country_code(),
        "account_type": random.choice(["personal", "corporate", "PEP", "high_risk"]),
        "risk_rating": random.choice(["low", "medium", "high", "critical"]),
        "pep_status": random.choice([True, False]),
        "opened_at": fake.date_between(start_date="-5y", end_date="-30d").isoformat(),
    }


def generate_accounts(n=500):
    accounts = [generate_account() for _ in range(n)]
    return pd.DataFrame(accounts)


def generate_transaction(account, start_date, end_date):
    amount = Decimal(random.uniform(10, 50000)).quantize(Decimal("0.01"))

    # 5% chance of structuring (just under threshold)
    if random.random() < 0.05:
        amount = Decimal("9975.00") + Decimal(random.uniform(0, 24)).quantize(Decimal("0.01"))

    # 2% chance of large layering transaction
    if random.random() < 0.02:
        amount = Decimal(random.uniform(100000, 500000)).quantize(Decimal("0.01"))

    method = random.choices(
        PAYMENT_METHODS,
        weights=[20, 15, 15, 10, 30, 10],
    )[0]

    beneficiary_country = fake.country_code()
    if random.random() < 0.08:
        beneficiary_country = random.choice(COUNTRIES_SANCTIONED)

    tx = {
        "tx_id": str(uuid.uuid4())[:12].upper(),
        "account_id": account["account_id"],
        "client_id": account["client_id"],
        "amount": float(amount),
        "currency": random.choice(["USD", "EUR", "GBP", "CHF"]),
        "timestamp": fake.date_time_between(start_date=start_date, end_date=end_date).isoformat(),
        "payment_method": method,
        "beneficiary_country": beneficiary_country,
        "beneficiary_name": fake.name(),
        "reference": fake.sentence(nb_words=6)[:80],
        "wire_type": random.choice(WIRE_TYPES) if method in ("wire", "swift") else None,
    }
    return tx


def generate_transactions(accounts_df, days=90, avg_per_account=30):
    start = datetime.now(timezone.utc) - timedelta(days=days)
    end = datetime.now(timezone.utc)
    transactions = []

    for _, account in accounts_df.iterrows():
        n = max(1, int(random.gauss(avg_per_account, avg_per_account // 3)))
        for _ in range(n):
            transactions.append(generate_transaction(account.to_dict(), start, end))

    df = pd.DataFrame(transactions)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


if __name__ == "__main__":
    accounts = generate_accounts(200)
    transactions = generate_transactions(accounts, days=60)

    accounts.to_csv("data/accounts.csv", index=False)
    transactions.to_csv("data/transactions.csv", index=False)

    print(f"Generated {len(accounts)} accounts, {len(transactions)} transactions")
    print(f"Date range: {transactions['timestamp'].min()} -> {transactions['timestamp'].max()}")
    print(f"Amount range: {transactions['amount'].min():.2f} - {transactions['amount'].max():.2f}")
