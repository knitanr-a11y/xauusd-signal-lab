# NEXT CHAT HANDOFF — GOLD V3 109C created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_109C_TRAIN_ONLY_LOSS_FEATURE_FILTER_REPLAY_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## Current context

109B completed READY:

```text
status: GOLD_V3_109B_LOSS_FEATURE_FINGERPRINT_READY_AUDIT_ONLY
decision: LOSS_FEATURE_FINGERPRINT_READY_FOR_109C_TRAIN_ONLY_REPLAY
ledger_rows: 5571
candidate_filter_rows: 127
```

109B found post-hoc loss-heavy candidates, including:

```text
entry_hour <= 5
m15_rsi14 <= 40.5041
m15_dist_atr >= -0.0219
entry_hour <= 3
h4_atr28 >= 46.2521
m15_dist_atr >= 0.1542
m15_rsi14 <= 37.7016
```

These are not approved filters. They require train-only validation.

## What 109C does

109C validates top 109B loss-feature families using train-only/walk-forward replay.

It reads:

```text
FX_OUTPUTS/gold_v3/109c/gold_v3_109_selected_base_policy_ledger.csv
FX_OUTPUTS/gold_v3/109bc/gold_v3_109b_candidate_filter_diagnostics.csv
```

It uses 109B only as a feature/op universe. It does **not** use 109B full-sample thresholds as final rules.

For each split:

```text
lookback_active_days: 20, 50
target_active_days: 5, 10
```

The script:

1. Selects candidate filter thresholds using train rows only.
2. Applies the selected filter to target rows.
3. Compares target retained performance vs target base.
4. Outputs whether train-only validation confirms the loss-feature filter idea.

## Files created

```text
docs/gold_v3/GOLD_V3_109C_TRAIN_ONLY_LOSS_FEATURE_FILTER_REPLAY_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_109c_train_only_loss_feature_filter_replay_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_109c_train_only_loss_feature_filter_replay.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_109C_CREATED_PENDING_RUN_20260614.md
```

## Run next

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_109c_train_only_loss_feature_filter_replay.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/109cc/paste_me.txt
```

## Expected decisions

```text
TRAIN_ONLY_LOSS_FEATURE_FILTER_PRIMARY_READY_FOR_REVIEW
TRAIN_ONLY_LOSS_FEATURE_FILTER_REVIEW_READY_NEEDS_HUMAN_DECISION
TRAIN_ONLY_LOSS_FEATURE_FILTER_NOT_CONFIRMED_KEEP_109_BASE
TRAIN_ONLY_LOSS_FEATURE_FILTER_BLOCKED_INPUT_INCOMPLETE
```

## Notes

`entry_hour` filters are allowed for train-only diagnostics, but if they survive, they should be treated as operational/calendar-style filters and reviewed separately before adoption.

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
