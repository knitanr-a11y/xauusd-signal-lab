# GOLD V3 Stage273 R2 External 2023–2024 Base Audit

正式状態: `GOLD_V3_273_R2_EXTERNAL_2023_2024_BASE_REJECTED_AUDIT_ONLY`

## Data / Tick

XMTrading-MT5 3 / GOLD# の長期bar exportは正常。

- M1 1,225,431 rows: 2023-01-03 01:00 through 2026-06-19 19:54
- H1 20,459 rows
- duplicate/non-monotonic/copy errors: 0
- gap fill: false

Tick metadata:

- 2023: 0 (`NO_TICKS_RETURNED`)
- 2024: 0
- 2025: 0
- 2026: 10,146,463 rows, only 2026-05-13 01:00:02.024 through 2026-06-19 19:54:58.803

The broker does not expose older tick history to this terminal. The >1GB 2026 tick file is not required for Stage273.

## Contract parity

R2 was recomputed from the new H1/M1 files using the frozen definition:

- H1 decision hour UTC08–11
- H1 ATR percentile100 `HIGH` (>=0.76)
- direction = completed H1 candle direction
- entry = first same-source M1 open at/after H1 close

2025 parity against Stage268/272:

- candidates: 193 / 193
- matched decision times: 193
- activation exact: 193
- direction exact: 193
- ATR14 max absolute difference: 3.55e-15

Therefore the external calculation reproduces the previous contract exactly.

## External universe

- total 182
- 2023: 74
- 2024: 108
- LONG: 92
- SHORT: 90

72 trading-hour paths were required to remain within each calendar-year source period.

## FIXED 48h

External 2023–2024:

- positive rate 47.80%
- mean +0.113 ATR
- median -0.396 ATR
- cost2 expectancy -1.35 USD/oz
- cost5 expectancy -4.35 USD/oz
- PF cost2 0.906
- median MAE -2.978 ATR
- q10 -5.868 ATR
- worst -16.213 ATR

2023 mean -0.425 ATR / median -0.636 / PF 0.774.
2024 mean +0.482 ATR but median -0.245 / cost2 -0.03 / PF 0.998.
LONG external mean -0.302 ATR / cost2 -4.27 / PF 0.754.

## FIXED 72h

External 2023–2024:

- positive rate 48.90%
- mean +0.087 ATR
- median -0.188 ATR
- cost2 expectancy -1.44 USD/oz
- cost5 expectancy -4.44 USD/oz
- PF cost2 0.921
- median MAE -3.223 ATR
- q10 -8.271 ATR
- worst -17.519 ATR

2023 mean -0.638 ATR / median -0.521 / PF 0.753.
2024 mean +0.584 ATR but median -0.144 / cost5 -2.72 / PF 1.014.
LONG external median -0.306 ATR / cost2 -3.02 / PF 0.853.

## Path composition

At 48h:

- PERSISTENT 60, mean +5.325 ATR
- DELAYED 24, mean +2.737 ATR
- FADE 31, mean -3.274 ATR
- EARLY_FAIL 60, mean -4.322 ATR
- MIXED 7, mean -0.528 ATR

FADE + EARLY_FAIL were 91/182 (50.0%), offsetting the positive path classes.

## Early rejection

The Stage272 exit families were designed to manage an existing R2 base edge. Since the external 48h and 72h base distributions fail on median, transaction-cost expectancy, PF, 2023 stability, and direction robustness, the 22-exit grid is not used to rescue the failed external period.

## Formal decision

- R2 remains a recent 2025–2026 regime-dependent observation.
- It is not a generalizable 2023–2026 edge.
- Classification: `RECENT_REGIME_DEPENDENT_PATH_EDGE_NOT_GENERALIZABLE`.
- No live promotion.
- Do not upload the full 2026 tick file.
- If tick verification is later required, export only narrow windows around forward candidates.
- Do not retune R2 or its exit rules on the same 2023–2026 data to rescue it.

Regression tests: 4/4 PASS.

Operating state: `NO_LIVE_PROMOTION_AUDIT_ONLY`
