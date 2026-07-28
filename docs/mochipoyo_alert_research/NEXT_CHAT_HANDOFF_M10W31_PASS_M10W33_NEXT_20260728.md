# MOCHIPOYO Alert Research — M10W31 PASS / M10W33 next

repo: `knitanr-a11y/xauusd-signal-lab`  
branch: `feature/mochipoyo-alert-research`

## Current state

`M10W31_PASS_M10W32_FROZEN_M10W33_PREREGISTERED_EVALUATION_READY_AUDIT_ONLY`

Keep collector, M7C, M8C and all eight loops running unchanged:

- M9V
- M9Y
- M10B
- M10E
- M10P
- M10P2
- M10W19
- M10W26

M10W26 continues from immutable MT5-server start `2026.07.28 15:58:00`. M10W26 BAT01 is permanently forbidden.

## M10W31 result

Uploaded package:

- `99_UPLOAD_PACKAGE(73).zip`
- SHA256 `7483f46087c5ed8cfb673dc0c34976a57387885738e5ecaa6a568f89b6612120`
- size 965,332 bytes
- built UTC `2026-07-28T14:07:33Z`

Formal result:

`config/mochipoyo_alert_research/m10w31_user_local_result_20260728.json`

Status:

`PASS_SCALE_NORMALIZED_CAUSAL_INFORMATION_AVAILABLE_AUDIT_ONLY`

Verified:

- exact M10W27 decision set: 7,480 rows
- train 3,640 / validation 3,193 / test 647
- missing context: 0
- non-positive H1 ATR: 0
- causal source timing violations: 0
- degenerate features: 0
- no future return, PF, PnL, label or trade-ledger use
- no M10W26 or existing-monitor modification

Stable selected features have train-versus-test PSI below 0.05. Absolute H1 ATR and spread representations have severe drift and are excluded from new family design.

M10W29 families remain closed. M10W31 does not rescue LMVI1, LMWR1 or LMMO1.

## M10W32 preregistration

Contract:

`config/mochipoyo_alert_research/m10w32_scale_normalized_entry_preregistration_20260728.json`

Exactly three semantic families are frozen:

1. `SNRI1_LONG_M5_NORMALIZED_RANGE_IMPULSE`
   - `m5_range3_over_h1_atr14 >= 0.40`
   - `m5_ret3_over_h1_atr14 > 0`
   - `m5_close_location >= 2/3`

2. `SNRC1_LONG_M15_NORMALIZED_RECLAIM_CONTINUATION`
   - `0 <= m15_close_minus_ema20_over_h1_atr14 <= 0.50`
   - `m5_ret3_over_h1_atr14 > 0`
   - `m5_close_location >= 0.60`

3. `SNDX1_LONG_DUAL_SCALE_NORMALIZED_EXPANSION`
   - `m5_range3_over_h1_atr14 >= 0.40`
   - `m1_range5_over_h1_atr14 >= 0.20`
   - `m1_ret5_over_h1_atr14 > 0`
   - `m1_close_location >= 0.60`

Thresholds are semantic and were checked only for non-trivial density. No outcome was used to select them.

## M10W33

Implementation audit:

`config/mochipoyo_alert_research/m10w33_preexecution_implementation_audit_20260728.json`

Operator:

`scripts/mochipoyo_alert_research/m10w33/bat/01_run_scale_normalized_entry_eval.bat`

Evaluation remains fixed:

- exact M1 entry
- exact M1 exit +240 minutes
- one position per family
- actual spread
- fixed $0.20 sensitivity
- +1bps / +2bps sensitivity
- train 2023–2024
- validation 2025
- test 2026
- frozen STRONG / ROBUST / REJECT tiers

Historical results are exploratory because earlier low-ATR outcomes and scale diagnosis are already known. Any advancement still requires a separate fresh prospective shadow.

## Next action

1. Keep all eight loops open.
2. Fetch/Pull `feature/mochipoyo-alert-research`.
3. Run:

`scripts/mochipoyo_alert_research/m10w33/bat/01_run_scale_normalized_entry_eval.bat`

4. Upload only:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W33\LATEST\99_UPLOAD_PACKAGE.zip`

## Permanent prohibitions

- no existing-loop BAT01/init/reset
- no M10W26 BAT01 or reinitialization
- no loop force-close/taskkill
- no manual lock/runtime/state/snapshot/adapter/journal edit or deletion
- no start reset or historical backfill
- no M10W29 family rescue
- no post-M10W33 formula/threshold/feature/session/spread/ATR/horizon/exit/runner tuning
- no M10V until M10P and M10P2 each have at least 20 resolved plus integrity PASS
- no Discord send
- no MT5 order
- no live-ready/final-signal/autopromotion
