# GOLD V2 23B request more audit human decision options audit spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `23B_REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_AUDIT_ONLY`
Mode: audit-only

## Purpose

23B is the next integrated audit-only step after 23A.

23B reads 23A audited artifacts as source-of-truth and creates a compact human decision options table. It does not select an option on behalf of the user and does not execute or prepare execution of any option.

## Current boundary

`REQUEST_MORE_AUDIT` is not source recovery approval.

23B must not execute, enable, prepare, approve, or finalize:

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

`FX_OUTPUTS/gold_v2_23a_request_more_audit_resolution_matrix_integrated_audit_only`

Required 23A files:

| role | file | expected |
| --- | --- | --- |
| 23A report | `GOLD_V2_23A_REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_INTEGRATED_AUDIT_ONLY_REPORT.md` | exists |
| 23A summary | `gold_v2_23a_request_more_audit_resolution_matrix_summary.json` | exists and status matches expected |
| 23A input audit | `gold_v2_23a_input_audit.csv` | exists and reports no missing required input |
| 23A resolution matrix | `gold_v2_23a_resolution_matrix.csv` | exists and has at least 9 rows |
| 23A integrated checks | `gold_v2_23a_integrated_checks.csv` | exists and has zero STOP rows |
| 23A required next gates | `gold_v2_23a_required_next_gates.csv` | exists and allows only 23B |
| 23A safety matrix | `gold_v2_23a_safety_matrix.csv` | exists and has zero STOP rows |

Expected 23A status:

`REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

Expected 23A selected/decision value:

`REQUEST_MORE_AUDIT`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_23b_request_more_audit_human_decision_options_audit_only`

Required output files from one script run:

| role | file | expected |
| --- | --- | --- |
| input audit | `gold_v2_23b_input_audit.csv` | 7 required input rows |
| decision options | `gold_v2_23b_human_decision_options.csv` | 8 decision option rows |
| integrated checks | `gold_v2_23b_integrated_checks.csv` | PASS/STOP rows for 23A and safety boundary |
| safety matrix | `gold_v2_23b_safety_matrix.csv` | confirms all forbidden actions remain false |
| required next gates | `gold_v2_23b_required_next_gates.csv` | allows only 23C after success; keeps recovery/live/external blocked |
| summary JSON | `gold_v2_23b_request_more_audit_human_decision_options_summary.json` | machine-readable status and outputs |
| report | `GOLD_V2_23B_REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md` | human-readable report |

## Expected counts

| item | expected count |
| --- | ---: |
| required 23A input artifacts | 7 |
| required 23B output artifacts | 7 |
| decision option rows | 8 |
| allowed next gate after 23B success | 1 |
| forbidden live/final/recovery/external gates after 23B | 8 |
| selected human decisions | 0 |
| AI API calls | 0 |
| Discord sends | 0 |
| MT5 orders | 0 |
| live hook calls | 0 |
| source recovery executions | 0 |
| source identity finalizations/recoveries | 0 |

## Trading ledger fields

23B does not evaluate trades and does not read trade ledgers.

The following trading fields are not applicable in 23B: `strategy_id`, `entry_time`, `direction`, `TP`, `SL`, `outcome`.

No source recovery, OHLC replay, component replay, or live evaluator reconstruction is performed.

## Decision option categories

23B may output only audit-only decision options:

- close the completed REQUEST_MORE_AUDIT read-only chain
- request 23C human decision intake audit-only
- request source recovery precheck audit-only
- request source identity finalization precheck audit-only
- request live evaluator precheck audit-only
- request final signal precheck audit-only
- request external action precheck audit-only
- request old GOLD/DISC8 de-quarantine precheck audit-only

Any option mentioning future approval must be marked as a future required value, not as a granted value.

## Success status

`REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

Success requires:

- all required 23A files exist
- 23A status matches expected status
- 23A `audit_only == true`
- 23A `integrated_audit_only == true`
- 23A selected and decision values remain `REQUEST_MORE_AUDIT`
- total upstream STOP rows are zero
- 23A allowed next gate is only `23B_REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_AUDIT_ONLY`
- 23A forbidden gates remain blocked
- 23A forbidden summary/external flags remain false
- 23A resolution matrix row count meets minimum
- 23A still-blocked list includes source identity finalization, source recovery, live, final signal, Discord, MT5, AI API, and live hook
- 23B safety matrix has zero STOP rows
- 23B selects no human decision value
- no AI API, Discord, MT5, live hook, live evaluator, final signal, source recovery, or finalization is called

## Stop conditions

The script must stop with non-zero exit code and write STOP outputs if any required check fails, including:

- missing 23A artifact
- unexpected 23A status
- `REQUEST_MORE_AUDIT` changed or missing
- upstream STOP rows present
- any recovery/finalization/live/final/external flag is true
- any forbidden gate is allowed
- 23A input audit reports missing required input
- 23A required next gate is not exactly 23B

## Files to inspect

Implementation files:

- `docs/gold_v2/GOLD_V2_23B_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`
- `docs/gold_v2/GOLD_V2_23B_REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_AUDIT_SPEC_20260606.md`
- `scripts/gold_v2_runtime/audit_gold_v2_23b_request_more_audit_human_decision_options.py`
- `scripts/gold_v2_runtime/bat/23B_DECISION_OPTIONS.bat`

Output files:

- `FX_OUTPUTS/gold_v2_23b_request_more_audit_human_decision_options_audit_only/GOLD_V2_23B_REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_23b_request_more_audit_human_decision_options_audit_only/gold_v2_23b_request_more_audit_human_decision_options_summary.json`
- `FX_OUTPUTS/gold_v2_23b_request_more_audit_human_decision_options_audit_only/gold_v2_23b_input_audit.csv`
- `FX_OUTPUTS/gold_v2_23b_request_more_audit_human_decision_options_audit_only/gold_v2_23b_human_decision_options.csv`
- `FX_OUTPUTS/gold_v2_23b_request_more_audit_human_decision_options_audit_only/gold_v2_23b_integrated_checks.csv`
- `FX_OUTPUTS/gold_v2_23b_request_more_audit_human_decision_options_audit_only/gold_v2_23b_required_next_gates.csv`
- `FX_OUTPUTS/gold_v2_23b_request_more_audit_human_decision_options_audit_only/gold_v2_23b_safety_matrix.csv`

## BAT execution order

Run only after 23A outputs already exist and have been reviewed:

1. `scripts\gold_v2_runtime\bat\23B_DECISION_OPTIONS.bat`

Do not run 23C automatically in the same step.

## What 23B implements

23B implements one integrated audit-only script that:

- loads 23A artifacts
- checks required upstream status and blockers
- writes input audit, integrated checks, safety matrix, required gates, human decision options, summary JSON, and Markdown report
- stops safely if the upstream source-of-truth state is not exactly the expected audit-only state

## What 23B does not implement

23B does not implement:

- choosing a decision value for the user
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
