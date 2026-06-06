# GOLD V2 24C source recovery evidence package review audit spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `24C_SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW_AUDIT_ONLY`
Mode: audit-only

## Purpose

24C reads 24B audited artifacts as source-of-truth and reviews whether the source recovery evidence package is complete enough to move to a gap-resolution planning step.

24C does not execute source recovery and does not approve source recovery.

Because 24B reported 3 open evidence gaps, 24C must keep source recovery execution blocked and route only to gap-resolution planning audit-only.

## Current boundary

24C must not execute, enable, prepare, approve, or finalize:

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

`FX_OUTPUTS/gold_v2_24b_source_recovery_evidence_inventory_audit_only`

Required 24B files:

| role | file | expected |
| --- | --- | --- |
| 24B report | `GOLD_V2_24B_SOURCE_RECOVERY_EVIDENCE_INVENTORY_AUDIT_ONLY_REPORT.md` | exists |
| 24B summary | `gold_v2_24b_source_recovery_evidence_inventory_summary.json` | exists and status matches expected |
| 24B input audit | `gold_v2_24b_input_audit.csv` | exists and reports no missing required input |
| 24B evidence inventory | `gold_v2_24b_evidence_inventory.csv` | exists and has at least 10 rows |
| 24B evidence gap matrix | `gold_v2_24b_evidence_gap_matrix.csv` | exists and has open gap rows |
| 24B integrated checks | `gold_v2_24b_integrated_checks.csv` | exists and has zero STOP rows |
| 24B required next gates | `gold_v2_24b_required_next_gates.csv` | exists and allows only 24C |
| 24B safety matrix | `gold_v2_24b_safety_matrix.csv` | exists and has zero STOP rows |

Expected 24B status:

`SOURCE_RECOVERY_EVIDENCE_INVENTORY_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24c_source_recovery_evidence_package_review_audit_only`

Required output files from one script run:

| role | file | expected |
| --- | --- | --- |
| input audit | `gold_v2_24c_input_audit.csv` | 8 required input rows |
| package review matrix | `gold_v2_24c_evidence_package_review_matrix.csv` | review rows derived from 24B inventory/gaps |
| gap resolution planning matrix | `gold_v2_24c_gap_resolution_planning_matrix.csv` | one row per open gap |
| integrated checks | `gold_v2_24c_integrated_checks.csv` | PASS/STOP rows for 24B and safety boundary |
| safety matrix | `gold_v2_24c_safety_matrix.csv` | confirms all forbidden actions remain false |
| required next gates | `gold_v2_24c_required_next_gates.csv` | allows only 24D gap-resolution plan audit-only after success |
| summary JSON | `gold_v2_24c_source_recovery_evidence_package_review_summary.json` | machine-readable status and outputs |
| report | `GOLD_V2_24C_SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW_AUDIT_ONLY_REPORT.md` | human-readable report |

## Expected counts

| item | expected count |
| --- | ---: |
| required 24B input artifacts | 8 |
| required 24C output artifacts | 8 |
| minimum package review rows | 10 |
| expected open gaps from 24B | 3 |
| source recovery executions | 0 |
| source recovery approvals granted | 0 |
| source identity finalizations/recoveries | 0 |
| AI API calls | 0 |
| Discord sends | 0 |
| MT5 orders | 0 |
| live hook calls | 0 |

## Trading ledger fields

24C does not evaluate trades and does not read trade ledgers for performance.

The following trading fields are not applicable in 24C: `strategy_id`, `entry_time`, `direction`, `TP`, `SL`, `outcome`.

No source recovery, OHLC replay, component replay, or live evaluator reconstruction is performed.

## Success status

`SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW_READY_AUDIT_ONLY_GAPS_OPEN_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Stop conditions

The script must stop with non-zero exit code and write STOP outputs if any required check fails, including:

- missing 24B artifact
- unexpected 24B status
- upstream STOP rows present
- any recovery/finalization/live/final/external flag is true
- any forbidden gate is allowed
- 24B input audit reports missing required input
- 24B required next gate is not exactly 24C
- evidence inventory is missing or too small
- gap matrix is missing

Open gaps are not a STOP condition for 24C. Open gaps are the reason to route to 24D gap-resolution planning audit-only. Open gaps must continue to block source recovery execution.

## Required future explicit values

24C does not grant these values. It only records that they would be required later.

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

- `docs/gold_v2/GOLD_V2_24C_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`
- `docs/gold_v2/GOLD_V2_24C_SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW_AUDIT_SPEC_20260606.md`
- `scripts/gold_v2_runtime/audit_gold_v2_24c_source_recovery_evidence_package_review.py`
- `scripts/gold_v2_runtime/bat/24C_SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW.bat`

Output files:

- `FX_OUTPUTS/gold_v2_24c_source_recovery_evidence_package_review_audit_only/GOLD_V2_24C_SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_24c_source_recovery_evidence_package_review_audit_only/gold_v2_24c_source_recovery_evidence_package_review_summary.json`
- `FX_OUTPUTS/gold_v2_24c_source_recovery_evidence_package_review_audit_only/gold_v2_24c_input_audit.csv`
- `FX_OUTPUTS/gold_v2_24c_source_recovery_evidence_package_review_audit_only/gold_v2_24c_evidence_package_review_matrix.csv`
- `FX_OUTPUTS/gold_v2_24c_source_recovery_evidence_package_review_audit_only/gold_v2_24c_gap_resolution_planning_matrix.csv`
- `FX_OUTPUTS/gold_v2_24c_source_recovery_evidence_package_review_audit_only/gold_v2_24c_integrated_checks.csv`
- `FX_OUTPUTS/gold_v2_24c_source_recovery_evidence_package_review_audit_only/gold_v2_24c_required_next_gates.csv`
- `FX_OUTPUTS/gold_v2_24c_source_recovery_evidence_package_review_audit_only/gold_v2_24c_safety_matrix.csv`

## BAT execution order

Run only after 24B outputs already exist and have been reviewed:

1. `scripts\gold_v2_runtime\bat\24C_SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW.bat`

Do not run 24D automatically in the same step.

## What 24C implements

24C implements one integrated audit-only script that:

- loads 24B artifacts
- verifies the inventory and blocked execution state
- reviews evidence package availability and open gaps
- writes package review and gap-resolution planning matrices
- writes input audit, integrated checks, safety matrix, required gates, summary JSON, and Markdown report

## What 24C does not implement

24C does not implement:

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
