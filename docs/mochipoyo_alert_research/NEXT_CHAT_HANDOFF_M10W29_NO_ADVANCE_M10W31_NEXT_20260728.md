# MOCHIPOYO Alert Research — M10W29 no advance / M10W31 next

repo: `knitanr-a11y/xauusd-signal-lab`  
branch: `feature/mochipoyo-alert-research`

## Current state

`M10W29_NO_ADVANCE_M10W30_SCALE_SHIFT_DIAGNOSED_M10W31_INFORMATION_AUDIT_READY_AUDIT_ONLY`

Keep collector, M7C, M8C and all eight private-snapshot loops running unchanged:

- M9V
- M9Y
- M10B
- M10E
- M10P
- M10P2
- M10W19
- M10W26

M10W26 immutable MT5-server start remains `2026.07.28 15:58:00`. M10W26 BAT01 is permanently forbidden. Restart only with BAT03 after an actual reviewed stop or incident.

## M10W29 result

Uploaded package: `99_UPLOAD_PACKAGE(72).zip`  
SHA256: `9584283d1a7079d50f33f360a616d1ff9b91dcf1e6a69797ef366f5e57919840`

Formal result:

`config/mochipoyo_alert_research/m10w29_user_local_result_20260728.json`

Status:

`PASS_NO_ADVANCING_LOW_ATR_MICROSTRUCTURE_ENTRY_FAMILY_AUDIT_ONLY`

All three exact M10W28 formulas were evaluated with exact M1 entry/exit, fixed 240-minute horizon and one-position-per-family. No formula, threshold or horizon changed.

- LMVI1: REJECT. Train PF 1.3091, validation PF 1.7044, 2026 PF 0.8792, all PF 1.4076, all +2bps PF 1.2309.
- LMWR1: WEAK_OR_INCONSISTENT. Train PF 1.3961, validation PF 1.6491, 2026 PF 1.0486, all PF 1.4574, all +2bps PF 1.2499.
- LMMO1: REJECT. Train PF 1.5119, validation PF 1.3644, 2026 PF 0.5806, all PF 1.3191, all +2bps PF 1.1492.

No family may advance. Do not change formula, threshold, feature, session, spread condition, ATR boundary, horizon, exit or runner based on these outcomes.

## M10W30 diagnostic

Formal result:

`config/mochipoyo_alert_research/m10w30_independent_covariate_shift_result_20260728.json`

Status:

`PASS_MATERIAL_2026_COVARIATE_SCALE_SHIFT_DIAGNOSTIC_ONLY`

This used only the uploaded M10W27 pre-entry feature rows. It did not read trade outcomes or trade ledgers.

2026 severe PSI features versus 2023-2024:

- last-closed M1 spread in bps
- M5 three-bar range in bps
- M1 five-bar range in bps
- M5 three-bar return in bps

Moderate PSI:

- M1 five-bar return in bps
- H1 ATR percentile100

The three frozen formula pass fractions remained broadly stable across train, validation and test. Therefore the issue is not a collapse in formula firing density. M10W30 is post-result diagnosis only and does not rescue or advance an M10W29 family.

## M10W31

Contract:

`config/mochipoyo_alert_research/m10w31_scale_normalized_causal_information_availability_contract_20260728.json`

Purpose:

Audit H1-ATR-normalized causal pre-entry information on the exact M10W27 7,480 decision-time cohort:

- M5 range3 / H1 ATR14
- M1 range5 / H1 ATR14
- M5 return3 / H1 ATR14
- M1 return5 / H1 ATR14
- M1 spread USD and spread / H1 ATR14
- M15 distance from EMA20 / H1 ATR14
- H1 distance from EMA20 / H1 ATR14
- existing scale-free volume and candle-shape controls

M10W31 does not create a candidate, formula or threshold and does not read returns, PF, PnL, labels, trade ledgers or future paths.

## Next action

1. Keep all eight loop windows open.
2. Fetch/Pull `feature/mochipoyo-alert-research`.
3. Run:

`scripts/mochipoyo_alert_research/m10w31/bat/01_run_scale_normalized_information_audit.bat`

4. Upload only:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W31\LATEST\99_UPLOAD_PACKAGE.zip`

Continue M10W26 without intervention. At 20 resolved, run its read-only BAT05 checkpoint.

## Permanent prohibitions

- no BAT01/init/reset for M9V, M9Y, M10B, M10E, M10P, M10P2 or M10W19
- never rerun M10W26 BAT01
- do not stop/restart healthy loops without an incident
- do not force-close or taskkill loops
- do not manually edit/delete runtime, state, lock, STOP, adapter, snapshot or journal files
- do not change any prospective start
- do not backfill before a start
- do not add nearest-M1 fallback
- do not rescue or retune M10W29 families
- do not create M10W31 formulas or thresholds before reviewing M10W31
- do not run M10V until M10P and M10P2 each have at least 20 resolved plus integrity PASS
- no Discord send
- no MT5 order
- no live-ready/final-signal/autopromotion
