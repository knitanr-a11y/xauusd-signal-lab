# NEXT CHAT HANDOFF — M10P + M10P2 dual fresh running, M10Q checkpoint ready

Date: 2026-07-27
Repo: knitanr-a11y/xauusd-signal-lab
Branch: feature/mochipoyo-alert-research

## Read first in the next chat
1. `docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M10P_M10P2_DUAL_FRESH_RUNNING_M10Q_NEXT_20260727.md`
2. `config/mochipoyo_alert_research/current_state_20260727.json`
3. `config/mochipoyo_alert_research/next_action_20260727.json`
4. `docs/mochipoyo_alert_research/M10P_AND_AFTER_SHORT_ADOPTION_ROADMAP_20260725.md`

## Current status
- audit-only
- collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2 are running and must remain unchanged
- M10P C056+G013 fresh shadow start: `2026.07.24 23:56:00` MT5 server time
- M10P2 C0212 fresh shadow start: `2026.07.27 01:39:00` MT5 server time
- M10P1 C0212 deterministic reproduction: PASS, 318 trades, all PF 1.4839437156621065, fixed $0.20 PF 1.4816933419152243, max reference diff 0.0
- M10Q dual fresh checkpoint auditor is implemented and read-only

## Frozen SHORT candidates
### M10P — C056 + G013
- h1_macd_hist_bps >= 3.637199446
- h1_macd_line_bps <= -7.667425443
- h1_ret3_bps >= 18.70087437
- d1_macd_hist_bps >= -14.25480242
- SHORT, 240 minutes, one-position

### M10P2 — C0212
- h4_ema20_30_bps >= 37.61355979
- h1_atr_pct100 >= 0.8
- M15 decision
- SHORT, 240 minutes, one-position

## Absolute prohibitions
- never rerun M10P BAT01
- never rerun M10P2 BAT01
- never change frozen starts
- never backfill PC-off gaps
- never use nearest M1 fallback
- latest CSV row is CLOSED by contract
- MT5 server time only; do not convert project decisions to JST
- no threshold refit from prospective outcomes
- no Discord send
- no MT5 order
- no live_ready
- no final_signal
- no automatic promotion
- do not stop/reset/reinitialize existing forward monitors for research convenience

## Feed guard incident and correction
Weekend market-closed wall time was incorrectly counted as feed age for M10P/M10P2. This was corrected without changing candidate formulas, thresholds, starts, or historical data. Freshness is now measured by observed M1 trading bars, preserving the former limits in trading-time terms:
- M5 10
- M15 30
- H1 120
- H4 480
- D1 2880 observed M1 bars

## Recovery after forced reboot
Use only:
`scripts/mochipoyo_alert_research/recovery/bat/01_recover_after_forced_reboot.bat`

Restart order:
1. MT5 / CSV export
2. collector
3. M7C
4. M8C
5. M9V
6. M9Y
7. M10B
8. M10E
9. M10P BAT03 only
10. M10P2 BAT03 only

Recovery preserves runtime manifests, starts, ledgers, and history. It may recover stale locks only. PC-off intervals not present in raw CSV remain unobserved and must never be backfilled.

## Review gates
M10P:
- 5 resolved: M10Q operational review
- 10: M10R interim review
- 20: M10S first formal fresh interpretation
- 40: M10T stability expansion
- 60: M10U adoption review

M10P2:
- 5 resolved: operational review
- 10: interim review
- 20: formal review

No PF2 claim before 20 resolved. No review automatically authorizes alert/demo/live use.

## M10Q checkpoint auditor
Operator:
`scripts/mochipoyo_alert_research/m10q/bat/01_run_dual_fresh_checkpoint_audit.bat`

Purpose:
- read M10P and M10P2 LATEST summaries/runtimes only
- verify immutable starts and safety flags
- report candidate / accepted / resolved / open / entry-gap / exit-gap / overlap counts
- report actual-spread and fixed-$0.20 metrics
- show reached review gates and next unresolved gate
- create `%LOCALAPPDATA%/xauusd_signal_lab/mochipoyo_alert_research/outputs/M10Q/LATEST/99_UPLOAD_PACKAGE.zip`

M10Q is safe to rerun and must not modify M10P/M10P2 runtime, start, thresholds, or ledgers.

## Next action
Keep both fresh SHORT shadows running. Run M10Q whenever a checkpoint review is desired, especially when either family approaches 5/10/20 resolved and M10P additionally 40/60. Upload only the M10Q `99_UPLOAD_PACKAGE.zip` for review.

Do not begin M10V SHORT-family portfolio comparison until sufficient independent fresh evidence exists. Continue M7C genuine source collection independently.
