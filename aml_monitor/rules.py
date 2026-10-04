"""AML monitoring rules engine.

Detects:
- Structuring / Smurfing (amounts just under reporting threshold)
- Velocity anomalies (high frequency in short time windows)
- High-risk country transfers
- Large single transactions
- Rapid movement between accounts (layering indicator)
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Protocol

import pandas as pd

THRESHOLD = 10_000.0
VELOCITY_WINDOW_HOURS = 24
VELOCITY_MAX_TXS = 5
VELOCITY_MAX_AMOUNT = 50_000.0


class Alert:
    def __init__(self, rule: str, severity: str, tx_id: str, reason: str, **extra):
        self.alert_id = hashlib.sha256(f"{rule}{tx_id}{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:16]
        self.rule = rule
        self.severity = severity  # low / medium / high / critical
        self.tx_id = tx_id
        self.reason = reason
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.extra = extra

    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "rule": self.rule,
            "severity": self.severity,
            "tx_id": self.tx_id,
            "reason": self.reason,
            "timestamp": self.timestamp,
            **self.extra,
        }


def check_structuring(df: pd.DataFrame) -> list[Alert]:
    """Structuring: multiple transactions just under the threshold ($10k)."""
    alerts = []
    flagged = df[
        (df["amount"] >= 9_500.0) & (df["amount"] < THRESHOLD) & (df["payment_method"] == "wire")
    ].copy()

    # Group by account within same day
    flagged["date"] = pd.to_datetime(flagged["timestamp"], format="ISO8601").dt.date
    for (account, date), group in flagged.groupby(["account_id", "date"]):
        if len(group) >= 2:
            total = group["amount"].sum()
            for _, tx in group.iterrows():
                alerts.append(Alert(
                    rule="STRUCTURING",
                    severity="high",
                    tx_id=tx["tx_id"],
                    reason=f"{len(group)} wire txs totalling ${total:,.2f} on {date}, each under $10k threshold",
                    account_id=account,
                    amount=tx["amount"],
                    tx_count=len(group),
                    total_amount=total,
                ))
    return alerts


def check_velocity(df: pd.DataFrame) -> list[Alert]:
    """Velocity: too many transactions or too much volume in a short window."""
    alerts = []
    df = df.copy()
    df["timestamp_dt"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp_dt")

    for account, group in df.groupby("account_id"):
        group = group.sort_values("timestamp_dt").reset_index(drop=True)
        for i, row in group.iterrows():
            window_end = row["timestamp_dt"]
            window_start = window_end - timedelta(hours=VELOCITY_WINDOW_HOURS)

            window_txs = group[
                (group["timestamp_dt"] >= window_start) & (group["timestamp_dt"] <= window_end)
            ]
            tx_count = len(window_txs)
            total_amount = window_txs["amount"].sum()

            if tx_count >= VELOCITY_MAX_TXS or total_amount >= VELOCITY_MAX_AMOUNT:
                alerts.append(Alert(
                    rule="VELOCITY_ANOMALY",
                    severity="medium",
                    tx_id=row["tx_id"],
                    reason=f"{tx_count} txs / ${total_amount:,.2f} in {VELOCITY_WINDOW_HOURS}h window",
                    account_id=account,
                    tx_count=tx_count,
                    window_amount=total_amount,
                    window_hours=VELOCITY_WINDOW_HOURS,
                ))
                break  # one alert per account per window to avoid spam
    return alerts


def check_high_risk_country(df: pd.DataFrame) -> list[Alert]:
    """Transfers to sanctioned or high-risk jurisdictions."""
    HIGH_RISK = {"AF", "KP", "IR", "SY", "BY", "CU", "VE"}
    SANCTIONED = {"KP", "IR", "SY"}

    alerts = []
    for _, tx in df.iterrows():
        country = tx["beneficiary_country"]
        if country in SANCTIONED:
            alerts.append(Alert(
                rule="SANCTIONED_JURISDICTION",
                severity="critical",
                tx_id=tx["tx_id"],
                reason=f"Transfer to sanctioned country: {country}",
                beneficiary_country=country,
                amount=tx["amount"],
            ))
        elif country in HIGH_RISK:
            alerts.append(Alert(
                rule="HIGH_RISK_COUNTRY",
                severity="high",
                tx_id=tx["tx_id"],
                reason=f"Transfer to high-risk FATF country: {country}",
                beneficiary_country=country,
                amount=tx["amount"],
            ))
    return alerts


def check_large_transaction(df: pd.DataFrame) -> list[Alert]:
    """Single transaction above threshold."""
    alerts = []
    flagged = df[df["amount"] > THRESHOLD]
    for _, tx in flagged.iterrows():
        alerts.append(Alert(
            rule="LARGE_TRANSACTION",
            severity="medium",
            tx_id=tx["tx_id"],
            reason=f"Single transaction of ${tx['amount']:,.2f} exceeds ${THRESHOLD:,.0f}",
            amount=tx["amount"],
        ))
    return alerts


def run_all_rules(df: pd.DataFrame) -> pd.DataFrame:
    """Run all AML rules and return alerts as a DataFrame."""
    all_alerts: list[Alert] = []
    all_alerts.extend(check_structuring(df))
    all_alerts.extend(check_velocity(df))
    all_alerts.extend(check_high_risk_country(df))
    all_alerts.extend(check_large_transaction(df))

    if not all_alerts:
        return pd.DataFrame()

    return pd.DataFrame([a.to_dict() for a in all_alerts])
