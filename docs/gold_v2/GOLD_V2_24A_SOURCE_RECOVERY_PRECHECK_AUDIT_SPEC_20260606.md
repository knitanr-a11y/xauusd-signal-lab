# GOLD V2 24A source recovery precheck audit spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `24A_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY`
Mode: audit-only

## Purpose

24A reads 23D routed artifacts as source-of-truth and creates a practical source recovery precheck package.

24A does not execute source recovery. It inventories prerequisites, evidence, blockers, and future explicit approval values that would be required before any source recovery execution could be considered later.

## Current boundary

24A must not execute, enable, prepare, approve, or finalize:

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

`FX_OUTPUTS/gold_v2_23d_request_more_audit_decision_routing_audit_only`

Required 23D files:

| role | file | expected |
| --- | --- | --- |
| 23D report | `GOLD_V2_23D_REQUEST_MORE_AUDIT_DECISION_ROUTING_AUDIT_ONLY_REPORT.md` | exists |
| 23D summary | `gold_v2_23d_request_more_audit_decision_routing_summary.json` | exists and status matches expected |
| 23D input audit | `gold_v2_23d_input_audit.csv` | exists and reports no missing required input |
| 23D routing matrix | `gold_v2_23d_decision_routing_matrix.csv` | exists and routes to 24A |
| 23D integrated checks | `gold_v2_23d_integrated_checks.csv` | exists and has zero STOP rows |
| 23D required next gates | `gold_v2_23d_required_next_gates.csv` | exists and allows only 24A |
| 23D safety matrix | `gold_v2_23d_safety_matrix.csv` | exists and has zero STOP rows |

Expected 23D status:

`REQUEST_MORE_AUDIT_DECISION_ROUTED_TO_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

Expected 23D route target:

`24A_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24a_source_recovery_precheck_audit_only`

Required output files from one script run:

| role | file | expected |
| --- | --- | --- |
| input audit | `gold_v2_24a_input_audit.csv` | 7 required input rows |
| precheck matrix | `gold_v2_24a_source_recovery_precheck_matrix.csv` | practical prerequisite/blocker rows |
| evidence request matrix | `gold_v2_24a_evidence_request_matrix.csv` | source evidence rows to inspect later |
| integrated checks | `gold_v2_24a_integrated_checks.csv` | PASS/STOP rows for 23D and safety boundary |
| safety matrix | `gold_v2_24a_safety_matrix.csv` | confirms all forbidden actions remain false |
| required next gates | `gold_v2_24a_required_next_gates.csv` | allows only 24B source recovery evidence inventory audit-only after success |
| summary JSON | `gold_v2_24a_source_recovery_precheck_summary.json` | machine-readable status and outputs |
| report | `GOLD_V2_24A_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY_REPORT.md` | human-readable report |

## Expected counts

| item | expected count |
| --- | ---: |
| required 23D input artifacts | 7 |
| required 24A output artifacts | 8 |
| minimum precheck matrix rows | 10 |
| minimum evidence request rows | 8 |
| source recovery executions | 0 |
| source recovery approvals granted | 0 |
| source identity finalizations/recoveries | 0 |
| AI API calls | 0 |
| Discord sends | 0 |
| MT5 orders | 0 |
| live hook calls | 0 |

## Trading ledger fields

24A does not evaluate trades and does not read trade ledgers.

The following trading fields are not applicable in 24A: `strategy_id`, `entry_time`, `direction`, `TP`, `SL`, `outcome`.

No source recovery, OHLC replay, component replay, or live evaluator reconstruction is performed.

## Success status

`SOURCE_RECOVERY_PRECHECK_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Stop conditions

The script must stop with non-zero exit code and write STOP outputs if any required check fails, including:

- missing 23D artifact
- unexpected 23D status
- 23D route target is not 24A
- upstream STOP rows present
- any recovery/finalization/live/final/external flag is true
- any forbidden gate is allowed
- 23D input audit reports missing required input
- 23D required next gate is not exactly 24A

## Required future explicit values

24A does not grant these values. It only records that they would be required later.

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

## Files to inspect

Implementation files:

- `docs/gold_v2/GOLD_V2_24A_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`
- `docs/gold_v2/GOLD_V2_24A_SOURCE_RECOVERY_PRECHECK_AUDIT_SPEC_20260606.md`
- `scripts/gold_v2_runtime/audit_gold_v2_24a_source_recovery_precheck.py`
- `scripts/gold_v2_runtime/bat/24A_SOURCE_RECOVERY_PRECHECK.bat`

Output files:

- `FX_OUTPUTS/gold_v2_24a_source_recovery_precheck_audit_only/GOLD_V2_24A_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_24a_source_recovery_precheck_audit_only/gold_v2_24a_source_recovery_precheck_summary.json`
- `FX_OUTPUTS/gold_v2_24a_source_recovery_precheck_audit_only/gold_v2_24a_input_audit.csv`
- `FX_OUTPUTS/gold_v2_24a_source_recovery_precheck_audit_only/gold_v2_24a_source_recovery_precheck_matrix.csv`
- `FX_OUTPUTS/gold_v2_24a_source_recovery_precheck_audit_only/gold_v2_24a_evidence_request_matrix.csv`
- `FX_OUTPUTS/gold_v2_24a_source_recovery_precheck_audit_only/gold_v2_24a_integrated_checks.csv`
- `FX_OUTPUTS/gold_v2_24a_source_recovery_precheck_audit_only/gold_v2_24a_required_next_gates.csv`
- `FX_OUTPUTS/gold_v2_24a_source_recovery_precheck_audit_only/gold_v2_24a_safety_matrix.csv`

## BAT execution order

Run only after 23D outputs already exist and have been reviewed:

1. `scripts\gold_v2_runtime\bat\24A_SOURCE_RECOVERY_PRECHECK.bat`

Do not run 24B automatically in the same step.

## What 24A implements

24A implements one integrated audit-only script that:

- loads 23D artifacts
- verifies the routed decision and blocked execution state
- writes source recovery precheck matrix and evidence request matrix
- writes input audit, integrated checks, safety matrix, required gates, summary JSON, and Markdown report

## What 24A does not implement

24A does not implement:

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
