# MOCHIPOYO Alert Research handoff — M10W22 PASS / M10W23 frozen / M10W24 next

repo: `knitanr-a11y/xauusd-signal-lab`
branch: `feature/mochipoyo-alert-research`

## Current formal state

`M10W22_PASS_M10W23_MICROSTRUCTURE_HYPOTHESES_FROZEN_M10W24_READY`

All existing forward monitors remain unchanged. M10W19 continues from immutable MT5 server start `2026.07.28 02:31:00`; its BAT01 is permanently forbidden and BAT03 remains the only restart path.

## M10W22 result

Uploaded package SHA256:
`3bc8fa6bd442a899fc2ee5281b672d24c0d8e2e9e69651ea228c3273f5c156ae`

Status:
`PASS_OUTCOME_BLIND_CAUSAL_INFORMATION_AVAILABLE_REAL_VOLUME_UNUSABLE`

Target regime rows: 8,648.

M1/M5 tick-volume, candle morphology, short-horizon return/range and spread features are almost completely available and non-degenerate. M1/M5 `real_volume` fields exist but are zero for all frozen rows and are unusable.

M10W22 did not read future returns, PF/PnL, win/loss labels, outcome correlations, or profit-ranked features.

## M10W23 preregistration

Contract:
`config/mochipoyo_alert_research/m10w23_high_atr_bullish_microstructure_entry_preregistration_20260728.json`

Target regime stays frozen:
- D1 EMA20 > EMA30 > EMA40
- H4 EMA20 > EMA30
- H1 TORYS MACD line > 0
- H1 Wilder ATR14 percentile100 >= 0.67

Exactly three new LONG families were frozen before outcome evaluation:

1. `MVI1_LONG_M5_VOLUME_IMPULSE`
   - `m5_tick_volume_ratio20 >= 1.0`
   - `m5_body_ratio >= 0.50`
   - `m5_close_location >= 2/3`

2. `MWR1_LONG_M5_PULLBACK_REJECTION`
   - `m5_ret3_bps <= 0`
   - `m5_lower_wick_ratio >= 0.40`
   - `m5_close_location >= 0.60`

3. `MMO1_LONG_M1_MICRO_MOMENTUM`
   - `m1_ret5_bps > 0`
   - `m1_up_close_count5 >= 3`
   - `m1_close_location >= 0.60`

Thresholds were chosen semantically and checked only for non-trivial historical density. No outcome was inspected.

After M10W24 results, threshold adjustment, feature combination search, feature addition/removal, session filtering, spread rescue, ATR boundary change and exit/horizon tuning are forbidden.

## M10W24

Stage:
`M10W24_PREREGISTERED_HIGH_ATR_BULLISH_MICROSTRUCTURE_ENTRY_EVALUATION_AUDIT_ONLY`

Operator:
`scripts/mochipoyo_alert_research/m10w24/bat/01_run_preregistered_microstructure_entry_evaluation.bat`

Output:
`%LOCALAPPDATA%/xauusd_signal_lab/mochipoyo_alert_research/outputs/M10W24/LATEST/99_UPLOAD_PACKAGE.zip`

Evaluation is fixed:
- 2023-2024 train
- 2025 validation
- 2026 test
- exact M1 entry/exit
- 240-minute horizon
- one-position per family
- actual spread
- fixed $0.20 sensitivity
- +1bps / +2bps sensitivity
- preregistered STRONG / ROBUST / REJECT tiers

Only ROBUST or STRONG may advance to a new independent fresh prospective shadow. Historical M10W24 results alone are never final support.

## Safety

- GOLD/XAUUSD only for new M10 research
- audit-only
- no historical backfill into forward
- no existing monitor modification
- no threshold refit
- M10W19 BAT01 forbidden
- M10P BAT01 forbidden
- M10P2 BAT01 forbidden
- M10V forbidden until M10P and M10P2 both have >=20 resolved with integrity PASS
- no Discord send
- no MT5 order
- no live_ready/final_signal
- no automatic live promotion
