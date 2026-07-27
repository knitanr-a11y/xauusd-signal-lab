# MOCHIPOYO Alert Research handoff — M10W16 no robust candidate / M10W17 next

repo: `knitanr-a11y/xauusd-signal-lab`
branch: `feature/mochipoyo-alert-research`

## M10W16 result

Uploaded package SHA256:
`12c933fef6b183c231efba95af562446d38bf842cdc6823ea965f0b5c95d9cd2`

Formal result:
`config/mochipoyo_alert_research/m10w16_user_local_preregistered_blind_spot_trend_continuation_result_20260728.json`

### BSC1 SHORT

Classification: `INSUFFICIENT_DENSITY`

- all actual PF: 1.1237092239306934
- all fixed0.20 PF: 1.1138368830761693
- all +2bps PF: 0.9763178342267902
- validation 2025 resolved count: 0

The 2025 zero is structural, not an implementation failure. M10W14 outcome-blind grid shows the exact prerequisite regime `D1 bearish + H4 EMA20-30 negative + H1 MACD line negative` had 3058 M15 windows in 2023, 160 in 2024, 0 in 2025 and 1928 in 2026. BSC1 trigger rates within that regime were ~7.65%, 5.63% and 7.83% in 2023, 2024 and 2026 respectively. The family is too regime-dependent to meet cross-year density requirements.

### BLC1 LONG

Classification: `WEAK_OR_INCONSISTENT`

- train 2023-24 PF: 1.1958195083121563
- validation 2025 PF: 1.2407617162342903
- test 2026 PF: 1.0113371405757994
- test 2026 +1bps PF: 0.9715385870540524
- test 2026 +2bps PF: 0.9331697173131642
- all actual PF: 1.19018488431914
- all +2bps PF: 1.0423429240032587

No M10W15 family may be tuned or advanced to fresh shadow from this result.

## Research interpretation

M10W14 found a real structural coverage blind spot, but the first preregistered trend-continuation event hypotheses did not turn it into robust edge. This does not justify threshold rescue. It means the next step should test whether the fixed blind-spot regime buckets themselves have stable directional opportunity before another trigger is invented.

## M10W17

Stage:
`M10W17_NEITHER_REGIME_DIRECTIONAL_OPPORTUNITY_AUDIT_ONLY`

Contract:
`config/mochipoyo_alert_research/m10w17_neither_regime_directional_opportunity_contract_20260728.json`

Operator:
`scripts/mochipoyo_alert_research/m10w17/bat/01_run_neither_regime_directional_opportunity_audit.bat`

Output:
`%LOCALAPPDATA%/xauusd_signal_lab/mochipoyo_alert_research/outputs/M10W17/LATEST/99_UPLOAD_PACKAGE.zip`

M10W17 uses only exact M10W14 `NEITHER` regime buckets. For each bucket it samples non-overlapping 240-minute observations and evaluates both directions across 2023-24 train / 2025 validation / 2026 test with actual spread, fixed $0.20 and +1/+2bps costs. Density and stability gates were frozen before execution. Bucket cuts cannot be changed or merged after outcomes.

If no bucket passes, the current coarse EMA/MACD/ATR regime space itself lacks stable unconditional blind-spot directionality under this test, and future research should add genuinely new information rather than keep tuning current thresholds.

If a bucket passes, it is still not a trade signal. A later causal event trigger must be preregistered inside that exact bucket and ultimately pass a new fresh prospective shadow.

## Safety

- GOLD/XAUUSD only for new M10 research
- audit-only
- keep all existing forward monitors unchanged
- M10P BAT01 forbidden
- M10P2 BAT01 forbidden
- M10V forbidden until both M10P and M10P2 reach 20 resolved with integrity PASS
- no Discord send
- no MT5 order
- no live_ready/final_signal
- no existing threshold/start/runtime reset
