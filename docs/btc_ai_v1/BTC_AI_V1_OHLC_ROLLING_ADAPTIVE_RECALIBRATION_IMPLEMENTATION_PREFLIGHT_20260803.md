# BTC AI V1 — OHLC rolling adaptive recalibration implementation preflight

Date: 2026-08-03  
Branch: `feature/btc-ai-v1-data-acquisition`  
Parent contract: `config/btc_ai_v1/ohlc_rolling_adaptive_recalibration_forensic_contract_20260803.json`

Formal preflight status:

`BTC_AI_V1_OHLC_ROLLING_ADAPTIVE_RECALIBRATION_IMPLEMENTATION_READY_FORMAL_EXECUTION_BLOCKED_MISSING_AUTHORITATIVE_STATE_INPUTS`

## What is complete

The frozen Stage 31 research schedule has been implemented without opening its outcomes:

- monthly EXPANDING, ROLLING_3M, ROLLING_6M and ROLLING_12M fitting;
- separate frozen LONG and SHORT LightGBM models;
- first closed M15 decision of each validation month as the refit time;
- resolved-only training history: `decision_time < refit_time` and `maturity_ns <= refit_time`;
- immediately preceding complete calendar month as the only P90 calibration window;
- exactly one validation pass for each month from 2024-01 through 2025-12;
- AUC, balanced accuracy, Brier, calibration slope, score PSI, feature PSI, P90 label lift and D1 decomposition;
- frozen support gates against EXPANDING;
- same rolling schedule must pass every gate for both LONG and SHORT;
- no direction, month, year, D1, Stage 29 or Stage 30 rescue;
- no candidate PnL and no automatic 2026 diagnostic.

## Causality audit

The implementation rejects or excludes:

- decisions at or after the monthly refit time from training;
- labels whose exact-M1 resolution/maturity is later than the refit time;
- calibration rows outside the immediately preceding complete month;
- any overlap between training/calibration and the validation month;
- any 2026 row from schedule selection;
- feature names indicating future outcomes, PnL, exits, MFE/MAE, volume or external-market data;
- state inputs other than exactly 100 frozen causal OHLC features.

Unit tests passed for:

1. unresolved-result exclusion at a monthly cutoff;
2. previous-complete-month-only calibration;
3. formal 24-month range ending before 2026;
4. PSI identity behavior;
5. expanding and rolling lookback boundaries.

A full synthetic smoke test traversed all `24 months × 4 schedules × 2 directions = 192` paths. All leakage counters were zero and the missing-input path failed closed with exit code 2. Synthetic metrics are implementation diagnostics only and are not BTC research evidence.

## Why formal execution is not claimed

The nine supplied stage archives contain code, contracts and accepted results through Stage 30, but not the authoritative generated Stage state matrix:

- `features.npy`
- `meta.csv`
- `feature_sets.json`

The cumulative master package intentionally excludes raw BTC candles. The currently available workspace also does not contain the accepted raw OHLC files required to regenerate those state inputs.

Formal Stage 31 metrics, schedule support, 2026 diagnostic and candidate PnL therefore remain unopened. No substitute, reconstructed, synthetic or differently sourced market data was used.

## Authoritative input required for the next formal execution

Preferred minimal input:

- Stage state directory generated from the accepted snapshot containing exactly:
  - `features.npy`
  - `meta.csv`
  - `feature_sets.json`

Alternative regeneration input:

- `BTCUSD#_M1_20230101_20260803.csv`
- `BTCUSD#_M15_20230101_20260803.csv`
- `BTCUSD#_H1_20230101_20260803.csv`
- `BTCUSD#_H4_20230101_20260802.csv`
- `BTCUSD#_D1_20230101_20260802.csv`

The source files must match `config/btc_ai_v1/source_data_manifest_20260803.json` before use. M5 remains available for source parity audit but is not required to construct the frozen 100-feature state matrix.

## Execution command

```powershell
python scripts/btc_ai_v1/run_ohlc_rolling_adaptive_recalibration_forensic.py `
  --state-dir "<authoritative-state-directory>" `
  --out-dir "<new-output-directory>" `
  --n-jobs 4
```

The output directory contains monthly metrics, prediction audit rows, feature PSI, leakage audit, schedule gates, result JSON, report and SHA256 manifest. It contains no trade PnL or deployment artifact.

## Authorization state

- candidate PnL: OFF
- 2026 schedule selection: OFF
- 2026 diagnostic: unopened until a 2024–2025 schedule passes
- portfolio: OFF
- Shadow: OFF
- Discord: OFF
- MT5 orders: OFF
- live-ready: OFF
- final signal: OFF
- PR merge: not authorized
