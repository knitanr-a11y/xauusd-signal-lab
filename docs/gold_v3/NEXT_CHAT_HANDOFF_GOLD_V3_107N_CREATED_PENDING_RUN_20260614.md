# NEXT CHAT HANDOFF — GOLD V3 107N created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_107N_TRAIN_ONLY_LOSS_TRIM_REPLAY_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## Current context

Stage107M is READY:

```text
GOLD_V3_107M_PROBLEM_REGIME_LOSS_TRIM_READY_AUDIT_ONLY
```

107M found a strong post-hoc diagnostic trim:

```text
best_filter: ALL m15_dist_atr >= 0.1153788860705594
base WR: 60.27%
base PF: 2.55
retained WR: 63.43%
retained PF: 2.93
retention: 79.92%
best_min_regime_wr: 63.25%
```

But this filter is not final:

```text
posthoc_filters_not_final=true
requires_train_only_revalidation=true
final_rule_approval=false
```

107M also found a very strong train-only candidate for 2026-04, but it must not be treated as final because it may be too month-specific:

```text
feature: m15_atr28
op: >=
threshold: 8.894285714285648
side_scope: LONG
target_month: 2026-04
target_retained_trades: 49
target_retained_wr: 100%
```

## What 107N does

107N performs monthly train-only / walk-forward replay:

1. For each target month, use only rows with `entry_dt < target_month_start` as training history.
2. Enumerate entry-known filters only on that training history.
3. Rank filters using training history only.
4. Apply the selected filter to the target month.
5. Aggregate monthly, regime, and total walk-forward performance.

This avoids selecting filters from the target month result.

## Files created

```text
docs/gold_v3/GOLD_V3_107N_TRAIN_ONLY_LOSS_TRIM_REPLAY_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_107n_train_only_loss_trim_replay_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107n_train_only_loss_trim_replay.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_107N_CREATED_PENDING_RUN_20260614.md
```

## Run next

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_107n_train_only_loss_trim_replay.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/107nc/paste_me.txt
```

## Important limitation

The current ledger still lacks `exit_dt`, so 107N is train-split proxy, not strict resolved-only live replay.

Even if 107N passes, the next step must still require a resolved ledger to prove:

```text
exit_dt <= current entry_dt
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
