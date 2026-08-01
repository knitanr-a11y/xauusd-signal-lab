# GOLD SCALP EVENT-FIRST V1 — Reproduction Note

Date: 2026-08-02

## Research environment

The research was executed in the assistant environment against retained validated DATA_V3 candles and the corrected causal fixed-dollar scalp outcome dataset. The user PC was not used for model training, event screening or backtesting.

## Essential source sizes

- exact M1 union: 1,266,508 rows;
- causal M5 decision rows: 251,967;
- source range: 2023-01-03 through 2026-07-31.

## Provisional lead reproducibility target

A correct reproduction must return:

- event: `REOPEN_GAPDOWN_RECLAIM_LONG_G0.25_R0.25`;
- model threshold: `0.732653477650135`;
- calibration selected trades: 13;
- calibration positive-PnL WR: 0.7692307692307693;
- calibration PF: 2.7385257301803674;
- evaluation selected trades: 16;
- evaluation wins: 11;
- evaluation positive-PnL WR: 0.6875;
- evaluation PF: 3.440666666666645;
- evaluation net: 36.60999999999967;
- evaluation DD: 3.0;
- independent exact-M1 mismatches: 0 PnL / 0 exit / 0 reason.

## Required reconstruction order

1. Rebuild the validated historical + sharp M5 union with sharp overlap priority after exact overlap equality checks.
2. Join to the corrected causal feature and fixed-dollar outcome table by `decision_time`.
3. Create `gap_abs = previous_completed_M5_close - current_M5_open`.
4. Create `fill_ratio = (current_M5_close - current_M5_open) / gap_abs`.
5. Keep only decision time 01:05, `gap_abs >= 0.25`, and `fill_ratio >= 0.25`.
6. Train the frozen small LightGBM through 2024-06-30.
7. Score 2024H2 and freeze its prediction median as the threshold.
8. Apply the frozen threshold from 2025 onward.
9. Apply one-position non-overlap after score filtering.
10. Re-evaluate accepted entries from exact M1 with TP5, SL3, 120 minutes, fixed spread 0.30, entry spread <= 30 points and SL-first same-minute collision.

## Restrictions

Pre-fix broad every-M5 calibration outputs are not valid evidence. The event threshold, model threshold and value contract must not be changed to improve retrospective results. No Shadow, Discord, MT5 order or live-trading authorization follows from this reproduction target.
