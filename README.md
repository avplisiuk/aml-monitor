# AML Transaction Monitor

Rule-based engine for detecting suspicious transaction patterns.
Implements five detection rules aligned with [FATF guidance](https://www.fatf-gafi.org/) and FinCEN red flags.

## What it detects

| Rule | Pattern | Severity |
|---|---|---|
| **Structuring / Smurfing** | Multiple wires just under $10k threshold in one day | High |
| **Velocity Anomaly** | >5 transactions or >$50k volume in 24h window | Medium |
| **Sanctioned Jurisdiction** | Transfer to OFAC-sanctioned countries (KP, IR, SY, etc.) | Critical |
| **High-Risk Country** | Transfer to FATF grey-list jurisdictions | High |
| **Large Transaction** | Single transaction exceeding $10k threshold | Medium |

## Quick start

```bash
pip install -r requirements.txt
python -m aml_monitor.main
```

## Run tests

```bash
pip install pytest
python -m pytest aml_monitor/tests.py -v
```

## Project structure

```
aml_monitor/
├── data_generator.py   # Synthetic data generator (Faker-based)
├── rules.py            # Detection rules + Alert model
├── main.py             # Entry point
└── tests.py            # Unit tests (5/5 passing)
requirements.txt
pyproject.toml
```

## How it works

### Structuring / Smurfing
Detects customers who deliberately split large amounts into multiple transactions just under the reporting threshold. Classic indicator of CTR evasion.

### Velocity Anomaly
Flags accounts with unusual transaction frequency or aggregate volume in a rolling 24-hour window.

### Sanctioned / High-Risk Jurisdictions
Cross-references beneficiary country codes against sanctions and high-risk jurisdiction lists.

### Large Transaction
Flags individual transactions exceeding standard monitoring thresholds.

## Limitations

- Synthetic data only (generated via Faker, no real PII)
- Rule-based engine (ML risk scoring can be layered on top)
- Sanctions country lists are hardcoded (production: integrate live OFAC SDN / UN feeds)

## Roadmap

- [ ] ML-based risk scoring model (XGBoost)
- [ ] Cycle detection for layering patterns
- [ ] Real sanctions list integration (OFAC SDN CSV)
- [ ] JSON/HTML alert reports
- [ ] Docker deployment

## License

MIT — see [LICENSE](LICENSE)
