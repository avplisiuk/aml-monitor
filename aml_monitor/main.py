"""Run AML monitoring rules and print summary."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_generator import generate_accounts, generate_transactions
from rules import run_all_rules


def main():
    os.makedirs("data", exist_ok=True)

    print("Generating synthetic data...")
    accounts = generate_accounts(n=200)
    transactions = generate_transactions(accounts, days=60)

    accounts.to_csv("data/accounts.csv", index=False)
    transactions.to_csv("data/transactions.csv", index=False)
    print(f"  -> {len(accounts)} accounts, {len(transactions)} transactions")

    print("Running AML rules...")
    alerts = run_all_rules(transactions)

    if alerts.empty:
        print("No alerts found.")
        return

    print(f"\nFound {len(alerts)} alerts:\n")
    print(alerts.groupby(["rule", "severity"]).size().to_string())

    print("\n--- Alert breakdown by rule ---")
    for rule in alerts["rule"].unique():
        subset = alerts[alerts["rule"] == rule]
        print(f"\n[{rule}] ({len(subset)} alerts, severities: {dict(subset['severity'].value_counts())})")
        for _, row in subset.head(3).iterrows():
            print(f"  - {row['tx_id']}: {row['reason']}")


if __name__ == "__main__":
    main()
