# GOLD V2 23D request more audit decision routing audit spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `23D_REQUEST_MORE_AUDIT_DECISION_ROUTING_AUDIT_ONLY`
Mode: audit-only

## Purpose

23D reads 23C validated artifacts as source-of-truth and routes one validated 23B `decision_value` to the next audit-only precheck step.

The user-selected value for this path is:

`REQUEST_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY`

This is a source recovery precheck request only. It is not source recovery approval.

## Current boundary

23D must not execute, enable, prepare, approve, or finalize:

- source recovery execution
- source identity finalization
- source identity recovery
- live evaluator
- live hook
- final signal
- Discord notification
- MT5 order
- AI API call

NO_SIGNAL must not send Discord.

Old GOLD/DISC8 remain quarantined because of suspected HTF open-time mismatch.

## Required prerequisite

Before running 23D, rerun 23C with one exact 23B decision value:

`REQUEST_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY`

23D must stop unless the 23C summary status is:

`REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

and `human_decision_value` equals:

`REQUEST_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY`

## Inputs

Source-of-truth input folder:

`FX_OUTPUTS/gold_v2_23c_request_more_audit_human_decision_intake_audit_only`

Required 23C files:

| role | file | expected |
| --- | --- | --- |
| 23C report | `GOLD_V2_23C_REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_AUDIT_ONLY_REPORT.md` | exists |
| 23C summary | `gold_v2_23c_request_more_audit_human_decision_intake_summary.json` | exists and validated status |
| 23C input audit | `gold_v2_23c_input_audit.csv` | exists and reports no missing required input |
| 23C allowed values | `gold_v2_23c_allowed_23b_decision_values.csv` | exists and contains selected decision value |
| 23C intake result | `gold_v2_23c_human_decision_intake_result.csv` | exists and validates selected decision value |
| 23C integrated checks | `gold_v2_23c_integrated_checks.csv` | exists and has zero STOP rows |
| 23C required next gates | `gold_v2_23c_required_next_gates.csv` | exists and allows only 23D after validated decision |
| 23C safety matrix | `gold_v2_23c_safety_matrix.csv` | exists and has zero STOP rows |

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_23d_request_more_audit_decision_routing_audit_only`

Required output files from one script run:

| role | file | expected |
| --- | --- | --- |
| input audit | `gold_v2_23d_input_audit.csv` | 8 required input rows |
| routing matrix | `gold_v2_23d_decision_routing_matrix.csv` | one route row |
| integrated checks | `gold_v2_23d_integrated_checks.csv` | PASS/STOP rows for 23C and routing boundary |
| safety matrix | `gold_v2_23d_safety_matrix.csv` | confirms all forbidden actions remain false |
| required next gates | `gold_v2_23d_required_next_gates.csv` | allows only source recovery precheck audit-only after success |
| summary JSON | `gold_v2_23d_request_more_audit_decision_routing_summary.json` | machine-readable status and outputs |
| report | `GOLD_V2_23D_REQUEST_MORE_AUDIT_DECISION_ROUTING_AUDIT_ONLY_REPORT.md` | human-readable report |

## Expected counts

| item | expected count |
| --- | ---: |
| required 23C input artifacts | 8 |
| required 23D output artifacts | 7 |
| routing matrix rows | 1 |
| selected decision values | 1 |
| execution approvals granted | 0 |
| AI API calls | 0 |
| Discord sends | 0 |
| MT5 orders | 0 |
| live hook calls | 0 |
| source recovery executions | 0 |
| source identity finalizations/recoveries | 0 |

## Trading ledger fields

23D does not evaluate trades and does not read trade ledgers.

The following trading fields are not applicable in 23D: `strategy_id`, `entry_time`, `direction`, `TP`, `SL`, `outcome`.

No source recovery, OHLC replay, component replay, or live evaluator reconstruction is performed.

## Success status

`REQUEST_MORE_AUDIT_DECISION_ROUTED_TO_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Stop conditions

The script must stop with non-zero exit code and write STOP outputs if any required check fails, including:

- missing 23C artifact
- 23C not in validated status
- 23C selected value is not `REQUEST_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY`
- upstream STOP rows present
- any recovery/finalization/live/final/external flag is true
- any forbidden gate is allowed
- 23C input audit reports missing required input
- 23C required next gate is not exactly 23D
- intake result does not validate the decision value

## Files to inspect

Implementation files:

- `docs/gold_v2/GOLD_V2_23D_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`
- `docs/gold_v2/GOLD_V2_23D_REQUEST_MORE_AUDIT_DECISION_ROUTING_AUDIT_SPEC_20260606.md`
- `scripts/gold_v2_runtime/audit_gold_v2_23d_request_more_audit_decision_routing.py`
- `scripts/gold_v2_runtime/bat/23D_DECISION_ROUTING.bat`

Output files:

- `FX_OUTPUTS/gold_v2_23d_request_more_audit_decision_routing_audit_only/GOLD_V2_23D_REQUEST_MORE_AUDIT_DECISION_ROUTING_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_23d_request_more_audit_decision_routing_audit_only/gold_v2_23d_request_more_audit_decision_routing_summary.json`
- `FX_OUTPUTS/gold_v2_23d_request_more_audit_decision_routing_audit_only/gold_v2_23d_input_audit.csv`
- `FX_OUTPUTS/gold_v2_23d_request_more_audit_decision_routing_audit_only/gold_v2_23d_decision_routing_matrix.csv`
- `FX_OUTPUTS/gold_v2_23d_request_more_audit_decision_routing_audit_only/gold_v2_23d_integrated_checks.csv`
- `FX_OUTPUTS/gold_v2_23d_request_more_audit_decision_routing_audit_only/gold_v2_23d_required_next_gates.csv`
- `FX_OUTPUTS/gold_v2_23d_request_more_audit_decision_routing_audit_only/gold_v2_23d_safety_matrix.csv`

## BAT execution order

1. Rerun 23C with selected decision value:

`python scripts\gold_v2_runtime\audit_gold_v2_23c_request_more_audit_human_decision_intake.py --decision-value REQUEST_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY`

2. Run 23D:

`scripts\gold_v2_runtime\bat\23D_DECISION_ROUTING.bat`

Do not run the source recovery precheck automatically in the same step.

## What 23D implements

23D implements one integrated audit-only script that:

- loads validated 23C artifacts
- verifies the user-selected decision value
- routes it to the next audit-only precheck step
- writes input audit, integrated checks, safety matrix, required gates, routing matrix, summary JSON, and Markdown report

## What 23D does not implement

23D does not implement:

- source recovery execution
- source recovery approval
- source identity finalization
- live evaluator
- live hook
- final signal
- Discord notification
- MT5 order
- AI API review
- OHLC replay
- strategy/trade evaluation
