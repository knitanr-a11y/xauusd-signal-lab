# GOLD V2 24B source recovery evidence inventory audit spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `24B_SOURCE_RECOVERY_EVIDENCE_INVENTORY_AUDIT_ONLY`
Mode: audit-only

## Purpose

24B reads 24A audited artifacts as source-of-truth and inventories evidence availability, gaps, and required next evidence-gathering steps for source recovery precheck.

24B does not execute source recovery and does not approve source recovery.

## Current boundary

24B must not execute, enable, prepare, approve, or finalize:

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

`FX_OUTPUTS/gold_v2_24a_source_recovery_precheck_audit_only`

Required 24A files:

| role | file | expected |
| --- | --- | --- |
| 24A report | `GOLD_V2_24A_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY_REPORT.md` | exists |
| 24A summary | `gold_v2_24a_source_recovery_precheck_summary.json` | exists and status matches expected |
| 24A input audit | `gold_v2_24a_input_audit.csv` | exists and reports no missing required input |
| 24A precheck matrix | `gold_v2_24a_source_recovery_precheck_matrix.csv` | exists and has at least 10 rows |
| 24A evidence request matrix | `gold_v2_24a_evidence_request_matrix.csv` | exists and has at least 8 rows |
| 24A integrated checks | `gold_v2_24a_integrated_checks.csv` | exists and has zero STOP rows |
| 24A required next gates | `gold_v2_24a_required_next_gates.csv` | exists and allows only 24B |
| 24A safety matrix | `gold_v2_24a_safety_matrix.csv` | exists and has zero STOP rows |

Expected 24A status:

`SOURCE_RECOVERY_PRECHECK_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24b_source_recovery_evidence_inventory_audit_only`

Required output files from one script run:

| role | file | expected |
| --- | --- | --- |
| input audit | `gold_v2_24b_input_audit.csv` | 8 required input rows |
| evidence inventory | `gold_v2_24b_evidence_inventory.csv` | evidence rows derived from 24A requests |
| evidence gap matrix | `gold_v2_24b_evidence_gap_matrix.csv` | missing/gap/follow-up rows |
| integrated checks | `gold_v2_24b_integrated_checks.csv` | PASS/STOP rows for 24A and safety boundary |
| safety matrix | `gold_v2_24b_safety_matrix.csv` | confirms all forbidden actions remain false |
| required next gates | `gold_v2_24b_required_next_gates.csv` | allows only 24C evidence package review audit-only after success |
| summary JSON | `gold_v2_24b_source_recovery_evidence_inventory_summary.json` | machine-readable status and outputs |
| report | `GOLD_V2_24B_SOURCE_RECOVERY_EVIDENCE_INVENTORY_AUDIT_ONLY_REPORT.md` | human-readable report |

## Expected counts

| item | expected count |
| --- | ---: |
| required 24A input artifacts | 8 |
| required 24B output artifacts | 8 |
| minimum evidence inventory rows | 10 |
| minimum evidence gap rows | 1 |
| source recovery executions | 0 |
| source recovery approvals granted | 0 |
| source identity finalizations/recoveries | 0 |
| AI API calls | 0 |
| Discord sends | 0 |
| MT5 orders | 0 |
| live hook calls | 0 |

## Trading ledger fields

24B does not evaluate trades and does not read trade ledgers for performance.

The following trading fields are not applicable in 24B: `strategy_id`, `entry_time`, `direction`, `TP`, `SL`, `outcome`.

No source recovery, OHLC replay, component replay, or live evaluator reconstruction is performed.

## Evidence inventory semantics

24B may check whether path-like evidence scopes exist only when they are concrete local artifact paths under `FX_OUTPUTS` or repository-relative paths represented in already audited outputs.

24B must not infer that non-concrete evidence exists. Abstract evidence scopes must be marked as `NEEDS_EXPLICIT_ARTIFACT_LIST` or equivalent.

24B must not fetch external resources, call APIs, or reconstruct source identity from OHLC.

## Success status

`SOURCE_RECOVERY_EVIDENCE_INVENTORY_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Stop conditions

The script must stop with non-zero exit code and write STOP outputs if any required check fails, including:

- missing 24A artifact
- unexpected 24A status
- upstream STOP rows present
- any recovery/finalization/live/final/external flag is true
- any forbidden gate is allowed
- 24A input audit reports missing required input
- 24A required next gate is not exactly 24B
- 24A evidence request matrix is missing or too small
- 24A precheck matrix is missing or too small

## Required future explicit values

24B does not grant these values. It only records that they would be required later.

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

- `docs/gold_v2/GOLD_V2_24B_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`
- `docs/gold_v2/GOLD_V2_24B_SOURCE_RECOVERY_EVIDENCE_INVENTORY_AUDIT_SPEC_20260606.md`
- `scripts/gold_v2_runtime/audit_gold_v2_24b_source_recovery_evidence_inventory.py`
- `scripts/gold_v2_runtime/bat/24B_SOURCE_RECOVERY_EVIDENCE_INVENTORY.bat`

Output files:

- `FX_OUTPUTS/gold_v2_24b_source_recovery_evidence_inventory_audit_only/GOLD_V2_24B_SOURCE_RECOVERY_EVIDENCE_INVENTORY_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_24b_source_recovery_evidence_inventory_audit_only/gold_v2_24b_source_recovery_evidence_inventory_summary.json`
- `FX_OUTPUTS/gold_v2_24b_source_recovery_evidence_inventory_audit_only/gold_v2_24b_input_audit.csv`
- `FX_OUTPUTS/gold_v2_24b_source_recovery_evidence_inventory_audit_only/gold_v2_24b_evidence_inventory.csv`
- `FX_OUTPUTS/gold_v2_24b_source_recovery_evidence_inventory_audit_only/gold_v2_24b_evidence_gap_matrix.csv`
- `FX_OUTPUTS/gold_v2_24b_source_recovery_evidence_inventory_audit_only/gold_v2_24b_integrated_checks.csv`
- `FX_OUTPUTS/gold_v2_24b_source_recovery_evidence_inventory_audit_only/gold_v2_24b_required_next_gates.csv`
- `FX_OUTPUTS/gold_v2_24b_source_recovery_evidence_inventory_audit_only/gold_v2_24b_safety_matrix.csv`

## BAT execution order

Run only after 24A outputs already exist and have been reviewed:

1. `scripts\gold_v2_runtime\bat\24B_SOURCE_RECOVERY_EVIDENCE_INVENTORY.bat`

Do not run 24C automatically in the same step.

## What 24B implements

24B implements one integrated audit-only script that:

- loads 24A artifacts
- verifies the precheck and blocked execution state
- inventories requested evidence and gaps
- writes input audit, integrated checks, safety matrix, required gates, evidence inventory, gap matrix, summary JSON, and Markdown report

## What 24B does not implement

24B does not implement:

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
