# GOLD V2 23C request more audit human decision intake audit spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `23C_REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_AUDIT_ONLY`
Mode: audit-only

## Purpose

23C is the next integrated audit-only step after 23B.

23C reads 23B audited artifacts as source-of-truth, creates a human decision input template, and optionally validates one exact 23B `decision_value` supplied by the user.

23C does not choose a decision value on behalf of the user. It does not approve, execute, or prepare execution of any selected option.

## Current boundary

A blank upload-only turn, generic continuation instruction, or `REQUEST_MORE_AUDIT` is not a selected 23B decision value and is not source recovery approval.

23C must not execute, enable, prepare, approve, or finalize:

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

## Inputs

Source-of-truth input folder:

`FX_OUTPUTS/gold_v2_23b_request_more_audit_human_decision_options_audit_only`

Required 23B files:

| role | file | expected |
| --- | --- | --- |
| 23B report | `GOLD_V2_23B_REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md` | exists |
| 23B summary | `gold_v2_23b_request_more_audit_human_decision_options_summary.json` | exists and status matches expected |
| 23B input audit | `gold_v2_23b_input_audit.csv` | exists and reports no missing required input |
| 23B decision options | `gold_v2_23b_human_decision_options.csv` | exists and has 8 decision values |
| 23B integrated checks | `gold_v2_23b_integrated_checks.csv` | exists and has zero STOP rows |
| 23B required next gates | `gold_v2_23b_required_next_gates.csv` | exists and allows only 23C |
| 23B safety matrix | `gold_v2_23b_safety_matrix.csv` | exists and has zero STOP rows |

Expected 23B status:

`REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

Expected 23B selected/decision value:

`REQUEST_MORE_AUDIT`

## Optional human decision input

23C may receive one exact 23B `decision_value` by either:

1. command line: `--decision-value EXACT_23B_VALUE`
2. environment variable: `GOLD_V2_23C_DECISION_VALUE=EXACT_23B_VALUE`
3. JSON file placed in the 23C output folder before rerun: `gold_v2_23c_human_decision_input.json`

If no value is supplied, 23C must still succeed in template mode and write:

`gold_v2_23c_human_decision_input_template.json`

Template mode must not allow 23D routing.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_23c_request_more_audit_human_decision_intake_audit_only`

Required output files from one script run:

| role | file | expected |
| --- | --- | --- |
| input audit | `gold_v2_23c_input_audit.csv` | 7 required input rows |
| allowed decision values snapshot | `gold_v2_23c_allowed_23b_decision_values.csv` | 8 23B decision values |
| decision input template | `gold_v2_23c_human_decision_input_template.json` | blank template with allowed values |
| decision intake result | `gold_v2_23c_human_decision_intake_result.csv` | one intake result row |
| integrated checks | `gold_v2_23c_integrated_checks.csv` | PASS/STOP rows for 23B and intake validation |
| safety matrix | `gold_v2_23c_safety_matrix.csv` | confirms all forbidden actions remain false |
| required next gates | `gold_v2_23c_required_next_gates.csv` | allows WAIT in template mode, or 23D only after valid user-supplied value |
| summary JSON | `gold_v2_23c_request_more_audit_human_decision_intake_summary.json` | machine-readable status and outputs |
| report | `GOLD_V2_23C_REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_AUDIT_ONLY_REPORT.md` | human-readable report |

## Expected counts

| item | expected count |
| --- | ---: |
| required 23B input artifacts | 7 |
| required 23C output artifacts | 9 |
| allowed 23B decision values | 8 |
| decision intake result rows | 1 |
| selected by script | 0 |
| execution approvals granted | 0 |
| AI API calls | 0 |
| Discord sends | 0 |
| MT5 orders | 0 |
| live hook calls | 0 |
| source recovery executions | 0 |
| source identity finalizations/recoveries | 0 |

## Trading ledger fields

23C does not evaluate trades and does not read trade ledgers.

The following trading fields are not applicable in 23C: `strategy_id`, `entry_time`, `direction`, `TP`, `SL`, `outcome`.

No source recovery, OHLC replay, component replay, or live evaluator reconstruction is performed.

## Success statuses

Template mode without a supplied value:

`REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_TEMPLATE_READY_AUDIT_ONLY_DECISION_NOT_SELECTED_SOURCE_RECOVERY_STILL_BLOCKED`

Validated mode with one exact 23B value:

`REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Stop conditions

The script must stop with non-zero exit code and write STOP outputs if any required check fails, including:

- missing 23B artifact
- unexpected 23B status
- `REQUEST_MORE_AUDIT` changed or missing
- upstream STOP rows present
- any recovery/finalization/live/final/external flag is true
- any forbidden gate is allowed
- 23B input audit reports missing required input
- 23B required next gate is not exactly 23C
- a supplied decision value is not one of the exact 23B decision values
- a supplied value starts with `APPROVE_`

## Files to inspect

Implementation files:

- `docs/gold_v2/GOLD_V2_23C_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`
- `docs/gold_v2/GOLD_V2_23C_REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_AUDIT_SPEC_20260606.md`
- `scripts/gold_v2_runtime/audit_gold_v2_23c_request_more_audit_human_decision_intake.py`
- `scripts/gold_v2_runtime/bat/23C_DECISION_INTAKE.bat`

Output files:

- `FX_OUTPUTS/gold_v2_23c_request_more_audit_human_decision_intake_audit_only/GOLD_V2_23C_REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_23c_request_more_audit_human_decision_intake_audit_only/gold_v2_23c_request_more_audit_human_decision_intake_summary.json`
- `FX_OUTPUTS/gold_v2_23c_request_more_audit_human_decision_intake_audit_only/gold_v2_23c_input_audit.csv`
- `FX_OUTPUTS/gold_v2_23c_request_more_audit_human_decision_intake_audit_only/gold_v2_23c_allowed_23b_decision_values.csv`
- `FX_OUTPUTS/gold_v2_23c_request_more_audit_human_decision_intake_audit_only/gold_v2_23c_human_decision_input_template.json`
- `FX_OUTPUTS/gold_v2_23c_request_more_audit_human_decision_intake_audit_only/gold_v2_23c_human_decision_intake_result.csv`
- `FX_OUTPUTS/gold_v2_23c_request_more_audit_human_decision_intake_audit_only/gold_v2_23c_integrated_checks.csv`
- `FX_OUTPUTS/gold_v2_23c_request_more_audit_human_decision_intake_audit_only/gold_v2_23c_required_next_gates.csv`
- `FX_OUTPUTS/gold_v2_23c_request_more_audit_human_decision_intake_audit_only/gold_v2_23c_safety_matrix.csv`

## BAT execution order

Run only after 23B outputs already exist and have been reviewed:

1. `scripts\gold_v2_runtime\bat\23C_DECISION_INTAKE.bat`

The default BAT runs template mode. It does not select a decision value.

Do not run 23D automatically unless 23C is rerun with one exact valid 23B decision value and the user explicitly instructs the next audit-only routing step.

## What 23C implements

23C implements one integrated audit-only script that:

- loads 23B artifacts
- validates 23B status, gates, blockers, and decision options
- writes an allowed-values snapshot and blank decision input template
- optionally validates one exact user-supplied 23B `decision_value`
- writes input audit, integrated checks, safety matrix, required gates, intake result, summary JSON, and Markdown report

## What 23C does not implement

23C does not implement:

- choosing a decision value for the user
- executing or approving the selected decision value
- source recovery execution
- source identity finalization
- live evaluator
- live hook
- final signal
- Discord notification
- MT5 order
- AI API review
- OHLC replay
- strategy/trade evaluation
