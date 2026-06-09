# GOLD V3 15 audit-only replay execution spec

Created: 2026-06-09

Status: `GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 15 executes an audit-only replay for the Stage 14 human-approved replay-plan preview rows.

The goal is to recompute true row-filtered replay metrics from GOLD V3 internal source artifacts:

```text
true trades per day
true win rate
true profit factor
true drawdown
monthly/fold-style stability
shared-entry-family overlap diagnostics
```

This stage is still audit-only.

It does **not** approve final candidates, finalize thresholds, train models, generate live signals, create ZIP output, call AI APIs, notify Discord, place MT5 orders, enable live hooks/evaluators, or create final signals.

## Required upstream

Stage 15 requires:

```text
GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_READY_AUDIT_ONLY
GOLD_V3_05_LABEL_FEATURE_JOIN_WALKFORWARD_READY_AUDIT_ONLY
```

Stage 14 supplies the approved replay-plan preview rows.

Stage 05 supplies the GOLD V3 label-feature join rows. These rows already combine Stage 03 label outcomes and Stage 04 entry-time features.

Stage 03 label outcomes were evaluated on canonical GOLD V3 M5 candles with SL-first same-bar priority, so Stage 15 does not use GOLD V2, old GOLD, or DISC8 artifacts.

## Quarantine boundary

Stage 15 must use only GOLD V3 artifacts.

GOLD V2, old GOLD, DISC8, and related legacy artifacts remain quarantined and must not be read, imported, compared, merged, recovered from, copied from, backfilled from, used as fallback, used as validation, used as replay input, used as feature source, used as rule source, used as candidate source, or used as source-of-truth.

## Inputs

Required GOLD V3 inputs:

```text
Files/FX_OUTPUTS/gold_v3/14_human_ranking_decision_intake_audit_only/gold_v3_14_summary.json
Files/FX_OUTPUTS/gold_v3/14_human_ranking_decision_intake_audit_only/gold_v3_14_replay_plan_preview.csv
Files/FX_OUTPUTS/gold_v3/14_human_ranking_decision_intake_audit_only/gold_v3_14_human_decision_intake_template.csv
Files/FX_OUTPUTS/gold_v3/05_label_feature_join_walkforward_split_audit_only/gold_v3_05_summary.json
Files/FX_OUTPUTS/gold_v3/05_label_feature_join_walkforward_split_audit_only/gold_v3_05_label_feature_join_rows.csv
Files/FX_OUTPUTS/gold_v3/05_label_feature_join_walkforward_split_audit_only/gold_v3_05_walkforward_fold_matrix.csv
```

Expected Stage 14 checks:

```text
summary.status == GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_READY_AUDIT_ONLY
approve_for_next_audit_only_replay_rows == 7
approved_entry_family_count == 3
replay_plan_preview_rows == 7
```

Expected Stage 05 checks:

```text
summary.status == GOLD_V3_05_LABEL_FEATURE_JOIN_WALKFORWARD_READY_AUDIT_ONLY
gold_v3_05_label_feature_join_rows.csv exists and is non-empty
```

## Replay method

For each Stage 14 approved replay-plan row:

1. Read `profile_id`, `direction`, `feature_column`, and `rule_expression_preview`.
2. Parse the rule expression.
3. Filter Stage 05 joined rows by:
   - exact `profile_id`
   - exact `direction`
   - rule expression on `feature_column`
4. Recompute metrics from `label_outcome` and `label_price_distance_result_usd`.

Supported rule expressions:

```text
feature >= value
feature <= value
lower <= feature <= upper
```

The current approved Stage 14 expressions include:

```text
h4_ret4 >= 0.00751699
3.59086 <= m15_atr28 <= 4.29321
h1_atr56 >= 9.95812
```

## Metrics

Candidate-level metrics:

```text
rows_replayed
unique_entry_times
calendar_days_in_trade_span
active_entry_dates
trades_per_calendar_day_true
trades_per_active_day_true
tp_count
sl_count
timeout_count
win_count_result_positive
loss_count_result_negative
breakeven_count_result_zero
win_rate_result_positive
tp_rate
avg_result_usd
median_result_usd
sum_result_usd
gross_profit_usd
gross_loss_abs_usd
profit_factor
max_drawdown_usd
max_consecutive_losses
best_trade_usd
worst_trade_usd
first_entry_time_utc
last_entry_time_utc
```

Family-level metrics:

```text
profile_count
profiles
profile_level_rows_total
unique_entry_times_family
profile_level_trades_per_calendar_day_true
unique_entry_times_per_calendar_day_true
best_profile_by_profit_factor
best_profile_profit_factor
best_profile_win_rate
best_profile_trades_per_calendar_day
```

Monthly metrics are written per candidate and `entry_month`.

## h1_atr56 shared-entry-family rule

The approved Stage 14 replay plan has 7 rows but only 3 entry families.

`GROUP_H1_ATR56_HIGH_VOL` contains five TP/SL/horizon profiles sharing the same entry condition:

```text
h1_atr56 >= 9.95812
```

These five rows must be replayed as profile comparisons, not counted as five independent entry ideas.

Stage 15 writes overlap diagnostics to make this explicit.

## Output directory

```text
Files/FX_OUTPUTS/gold_v3/15_audit_only_replay_execution/
```

The runtime follows the repaired GOLD V3 output-root convention and creates the output directory with:

```python
output_dir.mkdir(parents=True, exist_ok=True)
```

## Required outputs

The script must always write these outputs, including blocked/input-missing cases:

```text
gold_v3_15_summary.json
gold_v3_15_input_inventory.csv
gold_v3_15_replay_candidate_metrics.csv
gold_v3_15_replay_family_metrics.csv
gold_v3_15_replay_trade_ledger.csv
gold_v3_15_replay_monthly_metrics.csv
gold_v3_15_replay_overlap_audit.csv
gold_v3_15_decision_matrix.csv
gold_v3_15_blocker_matrix.csv
GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_REPORT.md
```

Exception runs may additionally write:

```text
gold_v3_15_exception.txt
```

ZIP output is disabled.

## Status values

Ready status:

```text
GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_READY_AUDIT_ONLY
```

Blocked status:

```text
GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_BLOCKED_AUDIT_ONLY
```

Exception status:

```text
GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_EXCEPTION_AUDIT_ONLY
```

## Blocker matrix

```text
G3-15-001 stage-14 approved replay plan: CLOSED only if Stage 14 READY and approved replay-plan rows are present
G3-15-002 stage-05 replay source: CLOSED only if Stage 05 READY and joined rows are readable
G3-15-003 feature columns: CLOSED only if all replay-plan feature columns exist in Stage 05 join rows
G3-15-004 rule parsing: CLOSED only if all rule expressions parse
G3-15-005 audit-only replay metrics: CLOSED only if candidate/family metrics and ledger are written
G3-15-006 final approval: CLOSED_BLOCKED_BY_POLICY
G3-15-007 threshold finalization: CLOSED_BLOCKED_BY_POLICY
G3-15-008 model training: CLOSED_BLOCKED_BY_POLICY
G3-15-009 signal/live: CLOSED_BLOCKED_BY_POLICY
G3-15-010 zip output: CLOSED_DISABLED
G3-15-011 external actions: CLOSED
G3-15-012 quarantined legacy artifacts: CLOSED only if no GOLD V2 / old GOLD / DISC8 artifacts are read
```

## Safety flags

These must remain false:

```text
auto_approval = false
final_candidate_approval = false
threshold_finalization = false
model_training = false
signals_generated = false
zip_output_created = false
ai_api_called = false
discord_enabled = false
mt5_enabled = false
live_hook_enabled = false
live_evaluator_enabled = false
final_signal_enabled = false
gold_v2_live_sot_used = false
quarantined_legacy_artifacts_read = false
```

`replay_executed` may be true only to indicate audit-only replay execution in Stage 15. It is not live replay and not final approval.

## Runtime script

```text
scripts/gold_v3_runtime/gold_v3_15_audit_only_replay_execution.py
```

CLI:

```text
python scripts/gold_v3_runtime/gold_v3_15_audit_only_replay_execution.py --repo-root <repo-root>
```

## BAT contract

BAT path:

```text
scripts/gold_v3_runtime/bat/GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION.bat
```

Because the BAT is under `scripts/gold_v3_runtime/bat/`, it must return to repo root with:

```bat
cd /d "%~dp0\..\..\.."
```

The BAT must run only:

```bat
python scripts\gold_v3_runtime\gold_v3_15_audit_only_replay_execution.py
```

or `py -3` fallback with the same script path.

The BAT must not call final approval, threshold finalization, training, signal, Discord, MT5, AI API, live hook, live evaluator, final signal, or ZIP processes.

## Success conditions

Stage 15 implementation is acceptable when:

```text
Stage 14 READY input is validated
Stage 05 READY input is validated
7 approved replay-plan rows are replayed
3 entry families are reported
candidate metrics are written
family metrics are written
trade ledger is written
monthly metrics are written
overlap audit is written
all safety guardrails remain false/blocked except audit-only replay execution
```

## Next action after this stage

After Stage 15 output is reviewed, the next stage may be a result-review / narrowing-decision stage.

That later stage is still not live approval and must not finalize thresholds unless explicitly authorized in a separate instruction.
