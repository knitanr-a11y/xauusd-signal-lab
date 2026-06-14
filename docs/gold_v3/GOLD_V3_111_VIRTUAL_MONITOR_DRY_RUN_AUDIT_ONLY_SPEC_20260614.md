# GOLD V3 Stage111 Spec — VIRTUAL_MONITOR_DRY_RUN_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_111_VIRTUAL_MONITOR_DRY_RUN_AUDIT_ONLY
```

## Why this stage exists

Stage110 completed audit-only monitoring design:

```text
status: GOLD_V3_110_AUDIT_MONITORING_DESIGN_READY_AUDIT_ONLY
decision: AUDIT_MONITORING_DESIGN_READY_FOR_STAGE111_VIRTUAL_MONITOR_DRY_RUN
selected_option: KEEP_107Q_BASE
selected_policy_key: 107Q_BASE_RESOLVED_PASS_THROUGH
health_gate_adopted: false
rolling_distribution_rows: 16546
monitoring_threshold_rows: 9
exit_dt_complete: 5571 / 5571
```

Stage111 dry-runs the virtual monitor using historical rolling distributions and thresholds.

## Purpose

Stage111 must:

1. Read Stage110 monitoring thresholds.
2. Read Stage110 historical rolling distribution.
3. Classify each rolling metric observation as OK/WATCH/CAUTION/STOP_REVIEW.
4. Summarize frequency by window and metric.
5. Identify latest historical monitor state.
6. Confirm no live hook, Discord, MT5, AI API, or final signal is enabled.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/110c/gold_v3_110_monitoring_thresholds.csv
FX_OUTPUTS/gold_v3/110c/gold_v3_110_historical_rolling_distribution.csv
FX_OUTPUTS/gold_v3/110c/gold_v3_110_summary.json
```

## Monitor classification

For each row and metric:

```text
value < stop_review_level  -> STOP_REVIEW
value < caution_level      -> CAUTION
value < watch_level        -> WATCH
else                       -> OK
```

These are audit-only states. They do not trigger Discord, MT5 execution, final signal, or live hook actions.

## Outputs

```text
FX_OUTPUTS/gold_v3/111c/gold_v3_111_virtual_monitor_events.csv
FX_OUTPUTS/gold_v3/111c/gold_v3_111_virtual_monitor_state_counts.csv
FX_OUTPUTS/gold_v3/111c/gold_v3_111_latest_monitor_state.csv
FX_OUTPUTS/gold_v3/111c/gold_v3_111_stop_review_examples.csv
FX_OUTPUTS/gold_v3/111c/gold_v3_111_monitor_dry_run_runbook.md
FX_OUTPUTS/gold_v3/111c/gold_v3_111_quality_gate_matrix.csv
FX_OUTPUTS/gold_v3/111c/gold_v3_111_blocker_matrix.csv
FX_OUTPUTS/gold_v3/111c/gold_v3_111_validation_matrix.csv
FX_OUTPUTS/gold_v3/111c/gold_v3_111_summary.json
FX_OUTPUTS/gold_v3/111c/GOLD_V3_111_VIRTUAL_MONITOR_DRY_RUN_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/111c/paste_me.txt
```

## Decision

Allowed decisions:

```text
VIRTUAL_MONITOR_DRY_RUN_READY_FOR_STAGE112_SELECTED_POLICY_AUDIT_FREEZE
VIRTUAL_MONITOR_DRY_RUN_BLOCKED_INPUT_INCOMPLETE
```

## Guardrails

GOLD V3 remains audit-only.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime, Stage69 runtime, live evaluator, live hook, final signal, Discord, MT5, or AI API.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 feature-only snapshot as a trading source.
