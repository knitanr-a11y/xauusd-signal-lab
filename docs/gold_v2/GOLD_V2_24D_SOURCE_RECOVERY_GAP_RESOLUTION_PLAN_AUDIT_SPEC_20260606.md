# GOLD V2 24D source recovery gap resolution plan audit spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `24D_SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_AUDIT_ONLY`
Mode: audit-only

## Purpose

24D reads 24C audited artifacts as source-of-truth and creates a concrete plan for resolving the 3 open evidence gaps.

24D does not resolve the gaps itself. It creates a blank artifact request template for 24E intake where exact artifact/path/hash entries must be supplied later.

24D does not execute source recovery and does not approve source recovery.

## Current boundary

24D must not execute, enable, prepare, approve, or finalize:

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

`FX_OUTPUTS/gold_v2_24c_source_recovery_evidence_package_review_audit_only`

Required 24C files:

| role | file | expected |
| --- | --- | --- |
| 24C report | `GOLD_V2_24C_SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW_AUDIT_ONLY_REPORT.md` | exists |
| 24C summary | `gold_v2_24c_source_recovery_evidence_package_review_summary.json` | exists and status matches expected |
| 24C input audit | `gold_v2_24c_input_audit.csv` | exists and reports no missing required input |
| 24C package review matrix | `gold_v2_24c_evidence_package_review_matrix.csv` | exists and has at least 10 rows |
| 24C gap resolution planning matrix | `gold_v2_24c_gap_resolution_planning_matrix.csv` | exists and has open gap plan rows |
| 24C integrated checks | `gold_v2_24c_integrated_checks.csv` | exists and has zero STOP rows |
| 24C required next gates | `gold_v2_24c_required_next_gates.csv` | exists and allows only 24D |
| 24C safety matrix | `gold_v2_24c_safety_matrix.csv` | exists and has zero STOP rows |

Expected 24C status:

`SOURCE_RECOVERY_EVIDENCE_PACKAGE_REVIEW_READY_AUDIT_ONLY_GAPS_OPEN_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24d_source_recovery_gap_resolution_plan_audit_only`

Required output files from one script run:

| role | file | expected |
| --- | --- | --- |
| input audit | `gold_v2_24d_input_audit.csv` | 8 required input rows |
| gap resolution plan | `gold_v2_24d_gap_resolution_plan.csv` | one plan row per open gap |
| artifact request template | `gold_v2_24d_artifact_request_template.csv` | blank intake template for 24E |
| integrated checks | `gold_v2_24d_integrated_checks.csv` | PASS/STOP rows for 24C and safety boundary |
| safety matrix | `gold_v2_24d_safety_matrix.csv` | confirms all forbidden actions remain false |
| required next gates | `gold_v2_24d_required_next_gates.csv` | allows only 24E artifact list intake audit-only after success |
| summary JSON | `gold_v2_24d_source_recovery_gap_resolution_plan_summary.json` | machine-readable status and outputs |
| report | `GOLD_V2_24D_SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_AUDIT_ONLY_REPORT.md` | human-readable report |

## Expected counts

| item | expected count |
| --- | ---: |
| required 24C input artifacts | 8 |
| required 24D output artifacts | 8 |
| expected open gaps carried forward | 3 |
| artifact request template rows | 3 |
| source recovery executions | 0 |
| source recovery approvals granted | 0 |
| source identity finalizations/recoveries | 0 |
| AI API calls | 0 |
| Discord sends | 0 |
| MT5 orders | 0 |
| live hook calls | 0 |

## Trading ledger fields

24D does not evaluate trades and does not read trade ledgers for performance.

The following trading fields are not applicable in 24D: `strategy_id`, `entry_time`, `direction`, `TP`, `SL`, `outcome`.

No source recovery, OHLC replay, component replay, or live evaluator reconstruction is performed.

## Success status

`SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Stop conditions

The script must stop with non-zero exit code and write STOP outputs if any required check fails, including:

- missing 24C artifact
- unexpected 24C status
- upstream STOP rows present
- any recovery/finalization/live/final/external flag is true
- any forbidden gate is allowed
- 24C input audit reports missing required input
- 24C required next gate is not exactly 24D
- 24C package review matrix is missing or too small
- 24C gap resolution planning matrix is missing or has no open gap row

Open gaps are expected in 24D and remain unresolved. 24D plans the artifact list intake only. It must not mark gaps as resolved.

## 24E intake fields

24D creates blank template rows for 24E. 24E must later receive exact values such as:

- artifact path
- artifact hash or blob SHA
- artifact role
- source identity scope
- upstream source-of-truth reference
- quarantine note when relevant

## Required future explicit values

24D does not grant these values. It only records that they would be required later.

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

- `docs/gold_v2/GOLD_V2_24D_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`
- `docs/gold_v2/GOLD_V2_24D_SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_AUDIT_SPEC_20260606.md`
- `scripts/gold_v2_runtime/audit_gold_v2_24d_source_recovery_gap_resolution_plan.py`
- `scripts/gold_v2_runtime/bat/24D_SOURCE_RECOVERY_GAP_RESOLUTION_PLAN.bat`

Output files:

- `FX_OUTPUTS/gold_v2_24d_source_recovery_gap_resolution_plan_audit_only/GOLD_V2_24D_SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_24d_source_recovery_gap_resolution_plan_audit_only/gold_v2_24d_source_recovery_gap_resolution_plan_summary.json`
- `FX_OUTPUTS/gold_v2_24d_source_recovery_gap_resolution_plan_audit_only/gold_v2_24d_input_audit.csv`
- `FX_OUTPUTS/gold_v2_24d_source_recovery_gap_resolution_plan_audit_only/gold_v2_24d_gap_resolution_plan.csv`
- `FX_OUTPUTS/gold_v2_24d_source_recovery_gap_resolution_plan_audit_only/gold_v2_24d_artifact_request_template.csv`
- `FX_OUTPUTS/gold_v2_24d_source_recovery_gap_resolution_plan_audit_only/gold_v2_24d_integrated_checks.csv`
- `FX_OUTPUTS/gold_v2_24d_source_recovery_gap_resolution_plan_audit_only/gold_v2_24d_required_next_gates.csv`
- `FX_OUTPUTS/gold_v2_24d_source_recovery_gap_resolution_plan_audit_only/gold_v2_24d_safety_matrix.csv`

## BAT execution order

Run only after 24C outputs already exist and have been reviewed:

1. `scripts\gold_v2_runtime\bat\24D_SOURCE_RECOVERY_GAP_RESOLUTION_PLAN.bat`

Do not run 24E automatically in the same step.

## What 24D implements

24D implements one integrated audit-only script that:

- loads 24C artifacts
- verifies the package review and blocked execution state
- creates one gap-resolution plan row per open gap
- creates blank artifact request template rows for 24E intake
- writes input audit, integrated checks, safety matrix, required gates, summary JSON, and Markdown report

## What 24D does not implement

24D does not implement:

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
