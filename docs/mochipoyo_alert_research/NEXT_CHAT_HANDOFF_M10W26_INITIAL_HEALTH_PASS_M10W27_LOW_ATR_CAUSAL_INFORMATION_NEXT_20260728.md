# MOCHIPOYO Alert Research handoff — M10W26 initial health PASS / M10W27 next

repo: `knitanr-a11y/xauusd-signal-lab`  
branch: `feature/mochipoyo-alert-research`

## Current formal state

`M10W26_INITIAL_HEALTH_PASS_RUNNING_M10W27_OUTCOME_BLIND_CAUSAL_INFORMATION_READY_AUDIT_ONLY`

All existing monitors remain audit-only. Keep collector, M7C, M8C and all eight private-snapshot loops running unchanged:

- M9V
- M9Y
- M10B
- M10E
- M10P
- M10P2
- M10W19
- M10W26

## M10W26 initial health result

Uploaded package:

- filename: `99_UPLOAD_PACKAGE(70).zip`
- SHA256: `656fd48b036076cf2a9f702ad45fafd55adf805d22837acecbff9fa6a5bc7833`
- size: 12,902 bytes
- built at UTC: `2026-07-28T13:03:15Z`

Formal result:

`config/mochipoyo_alert_research/m10w26_user_local_initial_health_result_20260728.json`

Status:

`PASS_M10W26_INITIAL_HEALTHY_RUNNING_AUDIT_ONLY`

Immutable MT5-server start:

`2026.07.28 15:58:00`

Verified:

- exactly one `run_m10w26_private_snapshot_v2.py` process
- one M10W26 lock
- V2 runtime contract
- frozen runtime and implementation SHA inventory
- runtime/state/start receipt/prestart audit start equality
- all six causal coverage families passed before start freeze
- short-family source timing violation count zero
- successful cycle count 1
- terminal failure count zero
- LATEST output PASS at the immutable start
- private snapshot receipt PASS
- all six private snapshot files verified
- all six shared journals verified
- no runtime/start mutation
- no historical backfill
- Discord OFF
- MT5 orders OFF
- live/final promotion OFF

Initial candidate, accepted, resolved and open counts were all zero. This is a normal initial observation immediately after the start and is not a strategy or runtime failure.

M10W26 BAT01 is now permanently forbidden. Restart M10W26 only with BAT03 after an actual stop or incident review.

Review gates remain:

- operational: 20 resolved
- interim: 60 resolved
- formal: 120 resolved
- automatic promotion: forbidden

## M10W27 rationale

M10W17 identified two stable unconditional LONG opportunity buckets inside the original NEITHER blind spot.

M10W26 covers the high-ATR bucket through the frozen MMO1 formula. The second stable bucket remains:

`D1_BULLISH | H4_POSITIVE | H1_MACD_POSITIVE | ATR_LOW_LT_0P33`

M10W17 historical summary for that bucket:

- all count: 614
- all PF: 1.3063793637777734
- fixed $0.20 PF: 1.3000171350274528
- +2bps PF: 1.126371044904125

This is regime-level historical evidence, not an entry signal. M10W27 therefore audits causal information availability only.

## M10W27 contract

`config/mochipoyo_alert_research/m10w27_low_atr_bullish_neither_causal_information_availability_contract_20260728.json`

Implementation review:

`config/mochipoyo_alert_research/m10w27_preexecution_implementation_audit_20260728.json`

M10W27 target:

- D1 EMA20 > EMA30 > EMA40
- H4 EMA20 > EMA30
- H1 TORYS MACD line > 0
- H1 Wilder ATR14 percentile100 < 0.33
- prefix-causal coverage class = NEITHER
- MT5 server time
- newest CSV row closed
- lower-timeframe source bar nominal close <= decision
- M1/M5 bar opening exactly at decision is forbidden

M10W27 reuses:

- exact M10W22 feature definitions
- exact M10W25 prefix-causal long-family engine
- exact M10W25 short-family engine

It inventories M1/M5 tick volume, candle morphology, micro momentum/range, spread and real-volume availability.

It does **not**:

- read or calculate future returns
- calculate PF or PnL
- read win/loss labels
- rank features by outcomes
- create an entry formula
- select a threshold
- modify M10W26 or any existing monitor

## Next operator action

1. Keep all eight loop windows open.
2. Fetch/Pull `feature/mochipoyo-alert-research`.
3. Run:

`script/mochipoyo_alert_research/m10w27/bat/01_run_low_atr_bullish_neither_causal_information_availability_audit.bat`

Correct path:

`scripts/mochipoyo_alert_research/m10w27/bat/01_run_low_atr_bullish_neither_causal_information_availability_audit.bat`

4. Upload only:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W27\LATEST\99_UPLOAD_PACKAGE.zip`

Continue M10W26 without intervention. When M10W26 reaches 20 resolved, run its read-only BAT05 health audit and upload the new package.

## Permanent prohibitions

- do not run BAT01/init/reset for M9V, M9Y, M10B, M10E, M10P, M10P2 or M10W19
- do not rerun M10W26 BAT01
- do not stop/restart healthy loops without an incident
- do not force-close or taskkill loops
- do not manually edit/delete runtime, state, prestart audit, lock, STOP, adapter, snapshot or journal files
- do not change any prospective start
- do not backfill before a start
- do not add nearest-M1 fallback
- do not create M10W27 entry formulas or thresholds before reviewing M10W27
- do not run M10V until M10P and M10P2 each have at least 20 resolved plus integrity PASS
- no Discord send
- no MT5 order
- no live-ready/final-signal/autopromotion
