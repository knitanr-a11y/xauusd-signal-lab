# NEXT CHAT HANDOFF — GOLD V3 107O created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_107O_ROLLING_20D_ADAPTIVE_LOSS_TRIM_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## Reason for 107O

The user correctly pointed out that month-based filter selection is too coarse. Stage107N used monthly train-only windows and did not confirm the trim:

```text
107N decision: TRAIN_ONLY_LOSS_TRIM_NOT_CONFIRMED_NEED_ALTERNATIVE_FILTERS
base WR: 60.27%
walkforward WR: 60.66%
base PF: 2.55
walkforward PF: 2.64
retention: 87.23%
min_regime_wr: 59.64%
negative_month_count: 1
primary_gate: false
review_gate: false
```

107N improved PF slightly, but the monthly approach selected filters that helped some months and damaged others. A rolling recent-history window should adapt faster.

## Progress display issue

The user also asked why the terminal no longer showed a clear percent progress display like older scripts.

107O restores explicit progress logging:

```text
progress   0.0% complete / 100.0% remaining | step 0/N | start
progress  25.0% complete /  75.0% remaining | step X/N | window=...
progress 100.0% complete /   0.0% remaining | step N/N | DONE
```

This is implemented by a `prog()` function in the script. Importing Python modules at the top of the file does not automatically create progress display; the script must explicitly print it.

## What 107O does

Stage107O performs rolling adaptive loss-trim replay with default parameters:

```text
lookback_active_days: 20
target_active_days: 5
min_train_rows: 300
min_removed: 15
min_retention: 65%
```

For each rolling window:

1. Use only the prior 20 active trade days as training history.
2. Select a loss-trim filter from that training history only.
3. Apply it to the next 5 active trade days.
4. Aggregate total / regime / monthly / window metrics.

## Files created

```text
docs/gold_v3/GOLD_V3_107O_ROLLING_20D_ADAPTIVE_LOSS_TRIM_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_107o_rolling_20d_adaptive_loss_trim_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107o_rolling_20d_adaptive_loss_trim.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_107O_CREATED_PENDING_RUN_20260614.md
```

## Run next

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_107o_rolling_20d_adaptive_loss_trim.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/107oc/paste_me.txt
```

## Important limitation

The current 107L ledger still lacks `exit_dt`. Therefore 107O is still a rolling train-split proxy, not strict resolved-only live replay.

Even if 107O passes, `live_ready` remains false until a resolved ledger proves:

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
