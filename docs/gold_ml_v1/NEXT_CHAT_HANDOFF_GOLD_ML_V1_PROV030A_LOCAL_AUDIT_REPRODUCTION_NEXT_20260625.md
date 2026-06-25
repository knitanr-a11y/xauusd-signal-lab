# GOLD_ML_V1 PROV-030-A — Local Audit Reproduction Next

Date: 2026-06-25

Formal status:

`GOLD_ML_V1_030_PROV030A_PROVISIONAL_COST_PASS_LOCAL_REPRODUCTION_READY_AUDIT_ONLY`

## Multi-view research result

Batch030 through Batch035 broadened the research beyond entry filters and loss subtraction:

- 12 event concepts and 24 directional families;
- LONG and SHORT;
- five entry modes;
- four exit-management profiles;
- 414 exact-M1 variants;
- diversified portfolio views;
- expanding walk-forward loss models;
- KMeans, shallow-tree and fixed-regime views;
- threshold sensitivity;
- cost stress;
- block bootstrap and leave-one-period-out checks.

One candidate reached provisional status:

`GML1-PROV-030-A`

Status:

`PROVISIONAL_COST_PASS_PROSPECTIVE_REQUIRED`

It is research-only and is not one of the accumulated frozen nine.

## Candidate

LONG H1/H4 uptrend with an M15 pullback through EMA50, local M15 EMA20 slope still negative, and strong D1 ADX. Entry requires a stop-style continuation confirmation within three closed M5 bars.

- SL: 1.0R;
- TP: 2.5R;
- move to breakeven after +1.0R;
- horizon: 24 hours;
- same-M1 ordering: stop first;
- risk: signal M15 Wilder ATR14.

The regime filter is applied before M5 confirmation and before one-open-position admission.

## Corrected audit metrics

- 2023: 58 trades, PF 1.379, mean +0.190R, total +11.0R, DD 10R;
- 2024: 77 trades, PF 1.728, mean +0.331R, total +25.49R, DD 9R;
- 2025: 87 trades, PF 1.848, mean +0.322R, total +28.05R, DD 10R;
- 2026 diagnostic: 25 trades, PF 1.042, mean +0.020R, total +0.5R, DD 7R.

Cost stress passed all 12 frozen spread/slippage scenarios. The worst 2024 scenario remained PF 1.295 and mean +0.168R; the worst 2025 scenario remained PF 1.464 and mean +0.212R.

Sixteen of 25 nearby threshold cells passed both 2024 and 2025 gates. The 2024-2025 month-block bootstrap 95% mean-R interval was approximately +0.070 to +0.529R.

## Caveats

- the final non-missing 2023 H1 selected leaf contains 11 trades;
- conservative multiplicity-adjusted monthly significance is not established;
- several individual quarters are negative;
- 2026 is nearly flat and weakens under higher costs;
- prospective audit-only confirmation is required before promotion.

## Local reproduction

The root launcher now performs a local audit reproduction from the exact six frozen RAW files. It fails closed unless the 247-row candidate trade registry SHA-256 equals:

`47912c3131f6917ecae31c13a797568aacca1a08a8b655721d5527e295e579c3`

User-facing launcher:

`RUN_GOLD_ML_V1_NEXT.bat`

Internal phase BAT:

`scripts/gold_ml_v1/exploration/windows/reproduce_prov030a.bat`

Output directory:

`outputs/gold_ml_v1/prov030a_local_reproduction`

After a local PASS, upload the selected `UPLOAD_THIS_GOLD_ML_V1.txt`. A separate prospective audit-only monitor may be prepared only after parity is confirmed.

## Still off

- accumulation into the frozen nine;
- registration;
- live signal;
- MT5 order;
- Discord;
- automatic promotion.
