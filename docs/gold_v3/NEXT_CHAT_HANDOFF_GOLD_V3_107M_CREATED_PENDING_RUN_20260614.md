# NEXT CHAT HANDOFF — GOLD V3 107M created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_107M_PROBLEM_REGIME_LOSS_TRIM_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## Current context

Stage107K2 / 107L found a promising balanced-60 policy:

```text
best_policy_key: density_safe||100||Q0.6
balanced_policy_rows: 84
all_regime_pass_65_count: 0
all_regime_pass_60_count: 12
best_min_wr: 0.601742696053306
best_min_pf: 2.5352617898638443
best_min_trades: 146
best_sum_trades: 8565
best_avg_wr: 0.6181773567575161
best_policy_rehydrated_rows: 8565
rehydration_metric_parity_pass: True
```

107L is blocked only because `exit_dt` is missing:

```text
missing_exit_dt_for_resolved_only_health_gate
```

This is not a strategy failure. It means rolling health gate cannot be simulated live-faithfully yet.

## Problem-side priority

The user requested that the problem side be prioritized.

From `gold_v3_107l_best_policy_monthly_diagnostics.csv`, the first performance problem is:

```text
REGIME_2026_Q1Q2 / 2026-03
trades: 188
wins: 69
losses: 119
WR: 36.70%
PF: 1.246865
unique_trade_days: 3
max_day_trade_share: 71.28%
```

Secondary weak months:

```text
2025-10 WR 52.76%
2025-07 WR 54.34%
2026-04 WR 55.08%
2025-11 WR 57.66%
```

The first target is therefore not 2026 high-vol. It is the weak 2026 Q1/Q2 cluster, especially March.

## Files created

```text
docs/gold_v3/GOLD_V3_107M_PROBLEM_REGIME_LOSS_TRIM_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_107m_problem_regime_loss_trim_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107m_problem_regime_loss_trim.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_107M_CREATED_PENDING_RUN_20260614.md
```

## What 107M does

Stage107M reads:

```text
FX_OUTPUTS/gold_v3/107lc/gold_v3_107l_best_policy_monthly_diagnostics.csv
FX_OUTPUTS/gold_v3/107lc/gold_v3_107l_rehydrated_best_policy_ledger.csv
```

It outputs:

```text
FX_OUTPUTS/gold_v3/107mc/paste_me.txt
```

It identifies problem months, side/month clusters, and audit-only loss-trim filter candidates using entry-known columns only.

It writes both:

```text
gold_v3_107m_loss_trim_frontier.csv
```

and:

```text
gold_v3_107m_train_only_loss_trim_candidates.csv
```

Important: post-hoc diagnostic filters are not final. Any promising filter must next be validated by train-only / walk-forward replay before it can become a real gate.

## Run next

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_107m_problem_regime_loss_trim.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/107mc/paste_me.txt
```

## Hard guardrails

GOLD V3 remains audit-only.

Do not read/use/reference/fallback to:

- GOLD V2
- old GOLD
- DISC8
- Stage41 feature-only snapshot as a trading source

Do not mutate:

- source CSVs
- CSV contract
- candidate pool
- Stage45 runtime
- Stage69 runtime
- live evaluator
- live hook
- final signal
- Discord
- MT5 execution
- AI API

Health / rolling gate rule:

```text
Only resolved outcomes with exit_dt <= current entry_dt may enter history.
```

CSV contract:

```text
open/in-progress candles are not written to CSV
CSV latest row is contractually closed
csv_open_bar_exclusion_required=false
```

Pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```
