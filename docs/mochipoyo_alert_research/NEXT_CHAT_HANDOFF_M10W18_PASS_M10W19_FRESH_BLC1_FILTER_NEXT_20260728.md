# MOCHIPOYO Alert Research handoff — M10W18 PASS / M10W19 fresh BLC1 filter next

repo: `knitanr-a11y/xauusd-signal-lab`
branch: `feature/mochipoyo-alert-research`

## Current formal state

`M10W18_EXACT_LOSS_REDUCTION_PASS_M10W19_FRESH_SHADOW_READY_AUDIT_ONLY`

All existing forward monitors remain unchanged and running. Existing immutable starts remain unchanged. M10P BAT01 and M10P2 BAT01 remain forbidden. M10V remains forbidden until M10P and M10P2 both reach 20 resolved with integrity PASS.

## M10W18 exact result

Uploaded package SHA256:
`aadc50e1a3f90783e049d4c8c956d841cae18c6d599ed7f7eff4a7caa450e6d0`

Formal result:
`config/mochipoyo_alert_research/m10w18_user_local_exact_blc1_atr_loss_reduction_result_20260728.json`

Frozen challenger gate:
- keep exact BLC1 formula
- ACCEPT only when `h1_atr_pct100 < 0.67`
- EXCLUDE `>=0.67` or unavailable
- 0.67 came from the outcome-blind M10W14 tercile boundary
- no other filter search allowed

Exact one-position rebuild result:
- baseline all PF 1.1901848843 -> filtered 1.3591452834
- baseline 2026 PF 1.0113371406 -> filtered 1.8047536670
- baseline all +2bps PF 1.0423429240 -> filtered 1.1811482340
- baseline all DD 862.5706 -> filtered 631.5769 bps
- filtered 2025 PF 1.4600785315
- filtered 2026 +2bps PF 1.6363835214
- train 2023-24 PF slightly decreased 1.1958195083 -> 1.1867621335

Capacity effect:
- 52 filtered accepted timestamps were not accepted in baseline because excluded HIGH-ATR trades had occupied capacity
- 49 of those new accepted trades resolved
- those 49 had PF 1.6693 and net +368.43 bps

Interpretation:
- material loss-reduction signal exists historically
- NOT clean historical validation because the gate was proposed after BLC1 outcomes were inspected
- historical adoption is forbidden
- no additional filter search from M10W18
- fresh prospective comparison is required

M10W17 context:
- aligned bullish HIGH ATR itself was a stable LONG opportunity bucket
- therefore HIGH ATR is not universally bad
- the observed weakness is specific to BLC1 zero-cross trigger x HIGH-ATR interaction

## M10W19

Stage:
`M10W19_BLC1_ATR_FILTER_FRESH_PROSPECTIVE_SHADOW`

Contract:
`config/mochipoyo_alert_research/m10w19_blc1_atr_filter_fresh_prospective_shadow_contract_20260728.json`

Two arms from the SAME new immutable fresh start:
- W0_BLC1_BASELINE: exact BLC1, no ATR gate
- W1_BLC1_ATR_FILTERED: exact BLC1 plus `h1_atr_pct100 < 0.67`

Both arms:
- MT5 server time
- closed rows only
- exact M1 entry/exit
- 240-minute horizon
- independent one-position allocation
- actual spread, fixed $0.20, +1/+2bps metrics
- no historical backfill
- no live action

Fresh review gates use FILTERED resolved counts:
- 20 operational descriptive review
- 60 interim review
- 120 formal review
- no automatic promotion at any gate

## Operator

After Fetch/Pull:

1. Run exactly once:
`scripts\mochipoyo_alert_research\m10w19\bat\01_initialize_fresh_shadow_once.bat`

2. Confirm `M10W19 INIT PASS` and record the printed immutable fresh start.

3. NEVER run M10W19 BAT01 again after INIT PASS.

4. Start and keep open:
`scripts\mochipoyo_alert_research\m10w19\bat\03_run_shadow_forever.bat`

5. After its first PASS cycle, upload:
`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W19\LATEST\99_UPLOAD_PACKAGE.zip`

Forced reboot recovery has been extended. Once M10W19 is initialized, restart it after recovery with BAT03 only.

## Safety

- GOLD/XAUUSD only for new M10 research
- audit-only
- no Discord send
- no MT5 orders
- no live_ready/final_signal
- do not modify existing monitors
- do not change M10W19 gate/formula after fresh start
- no historical backfill
- M10P/P2 BAT01 remain forbidden
- M10V remains forbidden before both M10P/P2 reach 20 resolved + integrity PASS
