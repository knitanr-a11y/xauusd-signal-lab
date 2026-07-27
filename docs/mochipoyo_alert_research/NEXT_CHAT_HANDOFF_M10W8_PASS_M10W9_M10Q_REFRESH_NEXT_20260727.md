# NEXT CHAT HANDOFF — M10W8 M9Y health PASS / M10W9 M10Q refresh next

Repo: `knitanr-a11y/xauusd-signal-lab`
Branch: `feature/mochipoyo-alert-research`

## Read first
1. this file
2. `config/mochipoyo_alert_research/current_state_20260727.json`
3. `config/mochipoyo_alert_research/next_action_20260727.json`
4. `config/mochipoyo_alert_research/m10w8_m9y_current_gold_payoff_result_20260727.json`
5. `config/mochipoyo_alert_research/m10w9_m10q_dual_short_checkpoint_refresh_contract_20260727.json`
6. `config/mochipoyo_alert_research/m10v_short_family_comparison_preregistration_20260727.json`

## Scope
Current new M10 research remains GOLD/XAUUSD only. M7C remains its already-frozen BTCUSD+XAUUSD background source-fidelity track and must remain unchanged.

## Keep all running monitors unchanged
collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2.

Immutable starts:
- M7C UTC `2026-07-20T14:54:15Z`
- M9V MT5 server `2026.07.24 11:04:00`
- M9Y `2026.07.24 12:45:00`
- M10B `2026.07.24 20:54:00`
- M10E `2026.07.24 22:06:00`
- M10P `2026.07.24 23:56:00`
- M10P2 `2026.07.27 01:39:00`

Never rerun M10P BAT01 or M10P2 BAT01. Do not reset/reinitialize M9V/M9Y/M10B/M10E.

## M10W8 — current M9Y fresh payoff review
Uploaded package SHA256:
`5dcc552e54c839629a1bcb1e5e5a07c563ff62c9d700304347f535c72dd3b9a1`

M9Y health/status:
- PASS_FRESH_PROSPECTIVE_AUDIT_ONLY
- upstream post-start S2_M15 = 5
- W1 reclaim entries = 3
- reclaim skips = 2
- pending = 0
- overlap skips = 0
- closed rows / exact M1 / no-nearest-fallback / prefix integrity all PASS

Y0 native:
- accepted/resolved/open = 3/3/0
- WR 66.67%
- PF 0.43896
- net -22.4744 bps
- DD 40.0583 bps

Y1 N6 native is identical to Y0 because all three accepted entries have N6=false.

Y2 runner50:
- n=3
- PF 0.41792
- net -23.3170 bps

Y3 runner75:
- n=3
- PF 0.40741
- net -23.7383 bps

N6:
- flagged entries = 0
- minimum risk-review gate = 10 flagged
- no N6 efficacy inference is allowed

Runner:
- only first accepted trade was runner-eligible
- native +14.8000 bps
- runner raw +13.1149 bps
- runner50 weighted +13.9574 bps
- runner75 weighted +13.5362 bps
- n=1 runner comparison is descriptive only

Two upstream S2 candidates failed the frozen W1 reclaim rule. Their later native outcomes include one large winner and one small loser. Do NOT use these post-outcome observations to widen/refit W1. The W1 rule remains frozen at 0.10 ATR / 10 minutes.

M9Y review gates from frozen contract:
- operational: Y0 accepted >=20
- interim: >=60
- N6 risk review: >=10 N6-flagged entries
- formal: >=120
- no automatic promotion

Current M9Y therefore remains healthy early accumulation only; no payoff/risk efficacy claim and no rule changes.

## M10W9 — next action
Refresh the existing read-only M10Q dual SHORT checkpoint after the additional fresh market interval.

Run:
`scripts/mochipoyo_alert_research/m10q/bat/01_run_dual_fresh_checkpoint_audit.bat`

Upload:
`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10Q\LATEST\99_UPLOAD_PACKAGE.zip`

This is a read-only refresh. It must not modify M10P/M10P2 runtimes, starts, ledgers, formulas, thresholds, one-position policy or historical-backfill policy.

The prior recorded M10Q had M10P=0 resolved and M10P2=0 resolved. Treat those counts as stale until the new M10Q package is reviewed.

M10V remains forbidden until BOTH M10P >=20 resolved and M10P2 >=20 resolved with integrity PASS. No early execution.

## Safety
Audit-only. No historical backfill, no future leakage, no nearest-M1 fallback, newest CSV row CLOSED, MT5 server time for project decisions, no threshold refit from fresh outcomes, no start reset, no Discord send, no MT5 orders, no live_ready, no final_signal, no automatic live promotion.
