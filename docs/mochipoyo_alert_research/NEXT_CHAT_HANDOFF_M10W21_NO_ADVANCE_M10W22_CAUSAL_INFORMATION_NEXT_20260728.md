# MOCHIPOYO Alert Research handoff — M10W21 no advance / M10W22 causal information next

repo: `knitanr-a11y/xauusd-signal-lab`
branch: `feature/mochipoyo-alert-research`

## Current formal state

`M10W21_NO_ADVANCING_ENTRY_FAMILY_M10W22_CAUSAL_INFORMATION_AUDIT_READY`

All existing forward monitors remain unchanged. M10W19 remains running from immutable MT5 server start `2026.07.28 02:31:00`; M10W19 BAT01 is permanently forbidden and restart is BAT03 only.

## M10W21 result

Uploaded package SHA256:
`7f0b95b52b71092c46e87a5e25bbd25d74ba5ef084410df79f74ecb4ec93268b`

Formal result:
`config/mochipoyo_alert_research/m10w21_user_local_preregistered_high_atr_bullish_entry_result_20260728.json`

Frozen target regime:
`D1 bullish + H4 EMA20>EMA30 + H1 MACD line>0 + H1 ATR percentile100>=0.67`

Results:
- HBR1 1-hour M15 breakout: REJECT. Train PF 0.8530, 2025 PF 0.9092, 2026 PF 1.0145, all PF 0.9056, all +2bps PF 0.8046.
- HER1 M15 EMA20 reclaim: REJECT. Train PF 1.5296, 2025 PF 1.1783, 2026 PF 0.7415, all PF 1.1705, all +2bps PF 1.0569.
- HRC1 M15 RCI9 oversold turn: INSUFFICIENT_DENSITY. Train PF 1.0691, 2025 PF 0.9809, 2026 n15 PF 1.4471, all PF 1.0667, all +2bps PF 0.9386.

No family may advance. Do not tune trigger parameters, combine triggers, add a session filter, change ATR boundary, horizon, runner or exit based on these outcomes.

## Interpretation

M10W17's HIGH-ATR bullish regime-level LONG directionality remains a research observation, but HBR1/HER1/HRC1 failed to robustly extract it as event entries. Therefore the next research step must use genuinely different causal information rather than parameter variants of EMA/MACD/RCI/simple breakout.

## M10W22

Stage:
`M10W22_HIGH_ATR_BULLISH_NEW_CAUSAL_INFORMATION_AVAILABILITY_AUDIT_ONLY`

Contract:
`config/mochipoyo_alert_research/m10w22_high_atr_bullish_new_causal_information_availability_contract_20260728.json`

Operator:
`scripts/mochipoyo_alert_research/m10w22/bat/01_run_high_atr_bullish_new_causal_information_availability_audit.bat`

Output:
`%LOCALAPPDATA%/xauusd_signal_lab/mochipoyo_alert_research/outputs/M10W22/LATEST/99_UPLOAD_PACKAGE.zip`

M10W22 is strictly outcome-blind. It audits only causally available pre-entry information inside the frozen target regime:
- M5 tick-volume ratio20
- M5 body / close-location / lower-wick / upper-wick ratios
- M5 3-bar micro-return and range
- M1 5-bar micro-return, up-close count, close-location and range
- last closed M1 spread in bps
- M1/M5 real_volume field availability

For every M15 decision, lower-timeframe bars are admitted only if their nominal close time is <= the decision timestamp. The M1/M5 bar opening at the decision itself is not available yet and must not be used.

Forbidden in M10W22:
- +240m or any future-return calculation
- PF/PnL/win-loss labels
- outcome correlations
- profit-ranked features
- feature threshold selection
- entry formula creation
- any M10W19 modification

Only after reviewing M10W22 may M10W23 preregister at most three simple microstructure entry families, with rules frozen before any outcome evaluation.

## Safety

- new M10 research GOLD/XAUUSD only
- audit-only
- no Discord send
- no MT5 orders
- no live_ready/final_signal
- no historical backfill into forward
- M10P BAT01 forbidden
- M10P2 BAT01 forbidden
- M10W19 BAT01 forbidden after initialization
- M10V forbidden until M10P and M10P2 both have >=20 resolved + integrity PASS
