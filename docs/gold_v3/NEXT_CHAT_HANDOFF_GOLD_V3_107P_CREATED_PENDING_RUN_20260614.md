# NEXT CHAT HANDOFF — GOLD V3 107P created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_107P_ROLLING_LOOKBACK_PARAMETER_SWEEP_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## Why 107P was created

Stage107O tested one rolling setting:

```text
lookback_active_days: 20
target_active_days: 5
```

107O was READY but not confirmed:

```text
status: GOLD_V3_107O_ROLLING_20D_ADAPTIVE_LOSS_TRIM_READY_AUDIT_ONLY
decision: ROLLING_20D_ADAPTIVE_LOSS_TRIM_NOT_CONFIRMED_NEED_PARAMETER_SWEEP
base_eval WR: 60.34%
rolling WR: 59.35%
base_eval PF: 2.624
rolling PF: 2.586
rolling_retention: 61.99%
min_regime_wr: 57.30%
primary_gate: false
review_gate: false
```

The user said that if 20 days is weak, 10 days and 5 days should also be tested.

## What 107P does

107P runs a rolling lookback/target parameter sweep:

```text
lookback_active_days: 20,10,5
target_active_days: 5,3,1
```

It tests 9 combinations:

```text
20->5, 20->3, 20->1
10->5, 10->3, 10->1
5->5, 5->3, 5->1
```

For each combination:

1. Use only prior rolling active-day history as train data.
2. Select the loss-trim filter from train only.
3. Apply it to the target active-day window.
4. Compare rolling output to the same-window base ledger.
5. Rank combos by WR/PF/min_regime/retention.

## Progress display

107P keeps explicit progress display:

```text
progress   0.0% complete / 100.0% remaining | step 0/N | start
progress  50.0% complete /  50.0% remaining | step X/N | combo=...
progress 100.0% complete /   0.0% remaining | step N/N | DONE
```

## Files created

```text
docs/gold_v3/GOLD_V3_107P_ROLLING_LOOKBACK_PARAMETER_SWEEP_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_107p_rolling_lookback_parameter_sweep_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107p_rolling_lookback_parameter_sweep.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_107P_CREATED_PENDING_RUN_20260614.md
```

## Run next

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_107p_rolling_lookback_parameter_sweep.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/107pc/paste_me.txt
```

## Important limitation

The 107L ledger still lacks `exit_dt`. Therefore 107P is still a rolling train-split proxy, not strict resolved-only live replay.

Even if 107P passes, `live_ready` remains false until a resolved ledger proves:

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
