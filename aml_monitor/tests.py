import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "aml_monitor"))

from data_generator import generate_accounts, generate_transactions
from rules import check_structuring, check_velocity, check_high_risk_country, check_large_transaction


def _make_transactions_with_structuring():
    accounts = generate_accounts(n=5)
    txs = generate_transactions(accounts, days=2, avg_per_account=10)

    # Inject structuring pattern: 3 wires at $9,900 on same day
    structuring = pd.DataFrame([
        {"tx_id": f"S{i}", "account_id": "ACC123", "client_id": "C123456",
         "amount": 9900.0 + i * 0.01, "currency": "USD",
         "timestamp": f"2025-01-15T10:{i:02d}:00", "payment_method": "wire",
         "beneficiary_country": "DE", "beneficiary_name": "Target",
         "reference": "test", "wire_type": "domestic"}
        for i in range(3)
    ])
    return pd.concat([txs, structuring], ignore_index=True)


def test_structuring_detects_under_threshold():
    txs = _make_transactions_with_structuring()
    alerts = check_structuring(txs)
    assert len(alerts) >= 1
    assert all(a.rule == "STRUCTURING" for a in alerts)


def test_no_structuring_when_below_threshold():
    accounts = generate_accounts(n=5)
    txs = generate_transactions(accounts, days=2, avg_per_account=5)
    alerts = check_structuring(txs)
    assert len(alerts) == 0


def test_large_transaction_detected():
    txs = pd.DataFrame([{
        "tx_id": "LT1", "account_id": "ACC1", "client_id": "C1",
        "amount": 150000.0, "currency": "USD",
        "timestamp": "2025-01-15T10:00:00", "payment_method": "wire",
        "beneficiary_country": "US", "beneficiary_name": "X",
        "reference": "test", "wire_type": "domestic",
    }])
    alerts = check_large_transaction(txs)
    assert len(alerts) == 1
    assert alerts[0].rule == "LARGE_TRANSACTION"


def test_sanctioned_country_detected():
    txs = pd.DataFrame([{
        "tx_id": "SC1", "account_id": "ACC1", "client_id": "C1",
        "amount": 5000.0, "currency": "USD",
        "timestamp": "2025-01-15T10:00:00", "payment_method": "wire",
        "beneficiary_country": "KP", "beneficiary_name": "X",
        "reference": "test", "wire_type": "domestic",
    }])
    alerts = check_high_risk_country(txs)
    assert len(alerts) == 1
    assert alerts[0].severity == "critical"


def test_velocity_alert():
    txs = pd.DataFrame([
        {
            "tx_id": f"V{i}", "account_id": "ACC_V", "client_id": "C1",
            "amount": 1000.0, "currency": "USD",
            "timestamp": f"2025-01-15T10:{i:02d}:00",
            "payment_method": "wire", "beneficiary_country": "US",
            "beneficiary_name": "X", "reference": "test", "wire_type": "domestic",
        }
        for i in range(6)
    ])
    alerts = check_velocity(txs)
    assert len(alerts) >= 1
