# MOCHIPOYO Alert Research handoff — M10W24 scope mismatch / M10W24B NEITHER correction next

repo: `knitanr-a11y/xauusd-signal-lab`
branch: `feature/mochipoyo-alert-research`

## Current formal state

`M10W24_SCOPE_MISMATCH_DIAGNOSED_M10W24B_NEITHER_CORRECTION_READY_AUDIT_ONLY`

All existing forward monitors remain running unchanged. M10W19 remains frozen at MT5 server time `2026.07.28 02:31:00`; BAT01 is permanently forbidden and BAT03 continues.

## M10W24 uploaded result

Uploaded package SHA256:
`167935382d79f780ab1f1d0f01dd8672b3186390a06cfb6d485cfcdba9d36c8a`

Execution itself passed. Broader high-ATR bullish cohort results:
- MVI1 REJECT, all PF 1.0736, +2bps PF 0.9597
- MWR1 REJECT, all PF 1.0823, +2bps PF 0.9580
- MMO1 REJECT, all PF 1.1362, +2bps PF 1.0028

Formal result:
`config/mochipoyo_alert_research/m10w24_user_local_broader_cohort_result_scope_mismatch_20260728.json`

## Scope mismatch discovered

M10W17's stable directional opportunity was explicitly discovered inside M10W14 `coverage_class=NEITHER` exact regime buckets, and its success meaning said later causal event-entry work should be designed inside that passing bucket.

M10W22 rebuilt the bullish/high-ATR regime directly from D1/H4/H1/ATR frozen bars but omitted the M10W14 `coverage_class=NEITHER` join/filter. Therefore M10W22 feature rows and M10W24 evaluation included windows outside the intended blind-spot cohort.

This is classified as cohort-scope implementation drift, not formula/threshold failure.

## M10W24B correction

Contract:
`config/mochipoyo_alert_research/m10w24b_neither_cohort_scope_correction_contract_20260728.json`

Operator:
`scripts/mochipoyo_alert_research/m10w24b/bat/01_run_neither_cohort_scope_correction.bat`

Output:
`%LOCALAPPDATA%/xauusd_signal_lab/mochipoyo_alert_research/outputs/M10W24B/LATEST/99_UPLOAD_PACKAGE.zip`

Correction only:
1. Read M10W22 `02_target_regime_causal_feature_rows.csv`.
2. Read M10W14 `02_m15_coverage_grid.csv`.
3. Exact join by `decision_time`.
4. Retain only `coverage_class=NEITHER`.
5. Re-evaluate the exact frozen M10W23 families MVI1/MWR1/MMO1.

Absolutely unchanged:
- MVI1/MWR1/MMO1 formulas
- all thresholds
- 240-minute horizon
- exact M1 execution
- one-position-per-family rule
- actual/fixed/+1/+2bps costs
- train/2025/2026 splits
- STRONG/ROBUST/REJECT decision tiers

M10W24 broader outcomes are already research-exposed, so M10W24B is not clean independent historical validation. Even if ROBUST/STRONG, support still requires a brand-new fresh prospective shadow with frozen rules.

## Safety

- GOLD/XAUUSD only
- audit-only
- no historical backfill into existing forward
- no existing monitor changes
- no threshold rescue
- M10W19 BAT01 forbidden
- M10P/M10P2 BAT01 forbidden
- M10V forbidden until both M10P and M10P2 reach 20 resolved with integrity PASS
- no Discord send / MT5 orders / live_ready / final_signal / auto promotion
