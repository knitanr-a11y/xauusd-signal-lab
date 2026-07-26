# NEXT CHAT HANDOFF — M10P + M10P2 dual fresh running, M10Q next

Date: 2026-07-27
Repo: knitanr-a11y/xauusd-signal-lab
Branch: feature/mochipoyo-alert-research

## Current status
- audit-only
- collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2 are intended to keep running unchanged
- M10P C056+G013 fresh shadow start: 2026.07.24 23:56:00 MT5 server time
- M10P2 C0212 fresh shadow start: 2026.07.27 01:39:00 MT5 server time
- M10P1 C0212 deterministic reproduction: PASS, 318 trades, all PF 1.4839437156621065, fixed $0.20 PF 1.4816933419152243, max reference diff 0.0

## Frozen SHORT candidates
### M10P
C056 + G013:
- h1_macd_hist_bps >= 3.637199446
- h1_macd_line_bps <= -7.667425443
- h1_ret3_bps >= 18.70087437
- d1_macd_hist_bps >= -14.25480242
- SHORT, 240 minutes, one-position

### M10P2
C0212:
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

The recovery path must preserve all runtime manifests, starts, ledgers, and history. It may recover stale locks only. PC-off intervals not present in raw CSV remain unobserved.

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

## Next implementation
Implement a read-only M10Q joint checkpoint auditor for M10P and M10P2. It should read each LATEST summary/runtime, verify immutable starts and safety flags, report candidate/accepted/resolved/open/gap counts, actual and fixed-$0.20 metrics, and state the next unresolved review gate. It must not modify either forward runtime or threshold.

Do not begin M10V SHORT-family portfolio comparison until sufficient independent fresh evidence exists. Continue M7C genuine source collection independently.
