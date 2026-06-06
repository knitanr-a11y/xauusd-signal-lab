# GOLD V2 23A request-more-audit resolution matrix integrated audit spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `23A_REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_INTEGRATED_AUDIT_ONLY`
Mode: audit-only

## Purpose

23A replaces the previous fragmented meta-audit pattern with one integrated audit-only script.

The script reads the 22G audited handoff artifacts as source-of-truth and produces a practical resolution matrix answering:

1. What uncertainty remains?
2. What evidence is missing?
3. What evidence already exists?
4. What is still blocked and why?
5. What exact human decision values would be required later?
6. What can be closed as complete from the `REQUEST_MORE_AUDIT` chain?
7. What is the fastest safe next move?

## Current boundary

`REQUEST_MORE_AUDIT` is not source recovery approval.

23A must not execute, enable, prepare, or finalize:

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

`FX_OUTPUTS/gold_v2_22g_additional_audit_read_only_final_handoff_audit_only`

Required source-of-truth files:

| role | file | expected |
| --- | --- | --- |
| 22G report | `GOLD_V2_22G_ADDITIONAL_AUDIT_READ_ONLY_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md` | exists |
| 22G final handoff | `GOLD_V2_22G_FINAL_HANDOFF_REQUEST_MORE_AUDIT_AUDIT_ONLY.md` | exists |
| 22G summary | `gold_v2_22g_additional_audit_read_only_final_handoff_summary.json` | exists and status matches expected |
| 22G input audit | `gold_v2_22g_input_audit.csv` | exists and reports no missing required upstream input |
| 22G handoff checks | `gold_v2_22g_handoff_checks.csv` | exists and has zero STOP rows |
| 22G required next gates | `gold_v2_22g_required_next_gates.csv` | exists and keeps forbidden gates blocked |
| 22G safety matrix | `gold_v2_22g_safety_matrix.csv` | exists and has zero STOP rows |

Expected 22G status:

`ADDITIONAL_AUDIT_READ_ONLY_FINAL_HANDOFF_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

Expected 22G selected/decision value:

`REQUEST_MORE_AUDIT`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_23a_request_more_audit_resolution_matrix_integrated_audit_only`

Required output files from one script run:

| role | file | expected |
| --- | --- | --- |
| input audit | `gold_v2_23a_input_audit.csv` | 7 required input rows |
| resolution matrix | `gold_v2_23a_resolution_matrix.csv` | at least 9 practical resolution rows |
| integrated checks | `gold_v2_23a_integrated_checks.csv` | PASS/STOP rows for 22G and safety boundary |
| safety matrix | `gold_v2_23a_safety_matrix.csv` | confirms all forbidden actions remain false |
| required next gates | `gold_v2_23a_required_next_gates.csv` | allows only 23B after success; keeps recovery/live/external blocked |
| summary JSON | `gold_v2_23a_request_more_audit_resolution_matrix_summary.json` | machine-readable status and outputs |
| report | `GOLD_V2_23A_REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_INTEGRATED_AUDIT_ONLY_REPORT.md` | human-readable report |

## Expected counts

| item | expected count |
| --- | ---: |
| required 22G input artifacts | 7 |
| required 23A output artifacts | 7 |
| minimum resolution matrix rows | 9 |
| allowed next gate after 23A success | 1 |
| forbidden live/final/recovery/external gates after 23A | 8 |
| AI API calls | 0 |
| Discord sends | 0 |
| MT5 orders | 0 |
| live hook calls | 0 |
| source recovery executions | 0 |
| source identity finalizations/recoveries | 0 |

## Trading ledger fields

23A does not evaluate trades and does not read trade ledgers.

The following trading fields are not applicable in 23A: `strategy_id`, `entry_time`, `direction`, `TP`, `SL`, `outcome`.

No source recovery or OHLC/live evaluator reconstruction is performed.

## Success status

`REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

Success requires:

- all required 22G files exist
- 22G status matches expected status
- 22G `final_handoff_ready == true`
- 22G selected and decision values remain `REQUEST_MORE_AUDIT`
- total upstream STOP rows are zero
- source recovery approval remains false
- source recovery execution remains false
- source identity finalization/recovery remain false
- live/final/external flags remain false
- forbidden next gates remain blocked
- 23A safety matrix has zero STOP rows
- no AI API, Discord, MT5, live hook, live evaluator, final signal, source recovery, or finalization is called

## Stop conditions

The script must stop with non-zero exit code and write STOP outputs if any required check fails, including:

- missing 22G artifact
- unexpected 22G status
- `REQUEST_MORE_AUDIT` changed or missing
- upstream STOP rows present
- any recovery/finalization/live/final/external flag is true
- any forbidden gate is allowed
- 22G input audit reports missing upstream input

## Human decision values required later

23A does not grant these values. It only documents that they would be required later.

| blocked action | required explicit value later |
| --- | --- |
| source recovery execution | `APPROVE_SOURCE_RECOVERY_EXECUTION` |
| source identity finalization | `APPROVE_SOURCE_IDENTITY_FINALIZATION` |
| live evaluator implementation | `APPROVE_LIVE_EVALUATOR_IMPLEMENTATION` |
| final signal | `APPROVE_FINAL_SIGNAL` |
| Discord send | `APPROVE_DISCORD_SEND` |
| MT5 order | `APPROVE_MT5_ORDER` |
| AI API review | `APPROVE_AI_API_REVIEW` |
| live hook | `APPROVE_LIVE_HOOK` |
| old GOLD/DISC8 de-quarantine | `APPROVE_OLD_GOLD_DISC8_DEQUARANTINE` |

## Files to inspect

Implementation files:

- `docs/gold_v2/GOLD_V2_23A_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`
- `docs/gold_v2/GOLD_V2_23A_REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_INTEGRATED_AUDIT_SPEC_20260606.md`
- `scripts/gold_v2_runtime/audit_gold_v2_23a_request_more_audit_resolution_matrix_integrated.py`
- `scripts/gold_v2_runtime/bat/23A_RESOLUTION_MATRIX.bat`

Output files:

- `FX_OUTPUTS/gold_v2_23a_request_more_audit_resolution_matrix_integrated_audit_only/GOLD_V2_23A_REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_INTEGRATED_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_23a_request_more_audit_resolution_matrix_integrated_audit_only/gold_v2_23a_request_more_audit_resolution_matrix_summary.json`
- `FX_OUTPUTS/gold_v2_23a_request_more_audit_resolution_matrix_integrated_audit_only/gold_v2_23a_input_audit.csv`
- `FX_OUTPUTS/gold_v2_23a_request_more_audit_resolution_matrix_integrated_audit_only/gold_v2_23a_resolution_matrix.csv`
- `FX_OUTPUTS/gold_v2_23a_request_more_audit_resolution_matrix_integrated_audit_only/gold_v2_23a_integrated_checks.csv`
- `FX_OUTPUTS/gold_v2_23a_request_more_audit_resolution_matrix_integrated_audit_only/gold_v2_23a_required_next_gates.csv`
- `FX_OUTPUTS/gold_v2_23a_request_more_audit_resolution_matrix_integrated_audit_only/gold_v2_23a_safety_matrix.csv`

## BAT execution order

Run only after 22G outputs already exist:

1. `scripts\gold_v2_runtime\bat\23A_RESOLUTION_MATRIX.bat`

Do not run 23B automatically in the same step.

## What 23A implements

23A implements one integrated audit-only script that:

- loads 22G artifacts
- checks required upstream status and blockers
- writes input audit, integrated checks, safety matrix, required gates, resolution matrix, summary JSON, and Markdown report
- stops safely if the upstream source-of-truth state is not exactly the expected audit-only state

## What 23A does not implement

23A does not implement:

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
