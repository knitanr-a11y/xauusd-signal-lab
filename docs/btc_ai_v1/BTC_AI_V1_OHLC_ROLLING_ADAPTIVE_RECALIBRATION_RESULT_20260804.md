# BTC AI V1 — Stage 31 rolling adaptive recalibration result

Date: 2026-08-04

Formal status:

`BTC_AI_V1_OHLC_ROLLING_ADAPTIVE_RECALIBRATION_NO_SUPPORTED_SCHEDULE`

## Formal conclusion

Monthly EXPANDING learning was compared with rolling 3-, 6- and 12-calendar-month learning under the frozen preregistration. All 24 validation months from 2024-01 through 2025-12 were evaluated exactly once for LONG and SHORT.

No rolling schedule passed every frozen support gate for both LONG and SHORT. Candidate PnL and the 2026 diagnostic remain unopened. No rescue, post-result direction selection, D1 filtering or gate reduction is authorized.

## Source and causal audit

- authoritative XM `BTCUSD#` M1/M5/M15/H1/H4/D1 hashes matched the frozen source manifest exactly;
- generated state frame: 125,567 rows × 100 frozen causal OHLC features;
- formal 2024–2025 decision rows: 70,066;
- 24 months × 4 schedules × 2 directions = 192 evaluations;
- available evaluations: 192; unavailable: 0;
- prediction-audit rows: 541,984;
- leakage violations: 0;
- training required `decision_time < refit_time` and `maturity_ns <= refit_time`;
- calibration used only the immediately preceding complete calendar month;
- 2026 selection rows: 0.

A representative formal path was recomputed independently and matched the stored metrics to floating-point rounding only, with maximum absolute difference `8.33e-17`.

## Absolute monthly means

| Schedule | Direction | Mean AUC | Mean P90 label lift | Mean Brier | Median score PSI |
|---|---|---:|---:|---:|---:|
| EXPANDING | LONG | 0.521667 | 0.053331 | 0.270842 | 0.126825 |
| EXPANDING | SHORT | 0.534568 | 0.063965 | 0.269431 | 0.129763 |
| ROLLING_3M | LONG | 0.515011 | 0.064861 | 0.286657 | 0.120478 |
| ROLLING_3M | SHORT | 0.509511 | 0.012996 | 0.280075 | 0.142688 |
| ROLLING_6M | LONG | 0.519844 | 0.041730 | 0.283133 | 0.103177 |
| ROLLING_6M | SHORT | 0.517725 | 0.024266 | 0.279855 | 0.113175 |
| ROLLING_12M | LONG | 0.522018 | 0.050914 | 0.278468 | 0.077060 |
| ROLLING_12M | SHORT | 0.524253 | 0.028079 | 0.274818 | 0.121556 |

## Frozen gate comparison against EXPANDING

| Schedule | Direction | Mean ΔAUC | Positive ΔAUC months | Mean ΔP90 lift | Positive ΔP90 months | Result |
|---|---|---:|---:|---:|---:|---|
| ROLLING_3M | LONG | -0.006656 | 12 | +0.011529 | 13 | FAIL |
| ROLLING_3M | SHORT | -0.025056 | 4 | -0.056627 | 5 | FAIL |
| ROLLING_6M | LONG | -0.001823 | 15 | -0.011602 | 14 | FAIL |
| ROLLING_6M | SHORT | -0.016842 | 5 | -0.039699 | 9 | FAIL |
| ROLLING_12M | LONG | +0.000351 | 11 | -0.002418 | 17 | FAIL |
| ROLLING_12M | SHORT | -0.010315 | 6 | -0.035885 | 5 | FAIL |

Required gates included mean ΔAUC at least +0.01, at least 15 positive ΔAUC months, mean ΔP90 lift at least +0.02, at least 15 positive ΔP90 months, positive lift in both years and all D1 regimes, limited half-year dependency and median score PSI at most 0.25.

## Interpretation

Hard recent-only windows did not solve the observed OHLC meaning drift. SHORT deteriorated under every rolling window. LONG showed isolated monthly improvements, but none were large and persistent enough to satisfy the preregistered mean and transfer gates.

One diagnostic month, `ROLLING_3M SHORT` in 2025-02, produced zero validation scores above the previous-month P90 threshold because of a large score-distribution shift. No threshold rescue was applied.

## Authorization state

- supported schedules: 0;
- supported candidates: 0;
- candidate PnL opened: no;
- 2026 opened: no;
- Shadow: OFF;
- Discord: OFF;
- MT5 orders: OFF;
- live-ready: OFF;
- final signal: OFF.
