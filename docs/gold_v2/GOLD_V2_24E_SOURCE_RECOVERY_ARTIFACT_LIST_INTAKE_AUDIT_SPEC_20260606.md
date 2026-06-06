# GOLD V2 24E source recovery artifact list intake audit spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `24E_SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_AUDIT_ONLY`
Mode: audit-only

## Purpose

24E reads 24D audited artifacts as source-of-truth and prepares/validates artifact list intake for the 3 open source recovery evidence gaps.

24E has two modes:

1. template/wait mode: no filled artifact list is supplied; 24E writes a fillable input template and does not allow 24F.
2. validation mode: a filled `gold_v2_24e_artifact_list_input.csv` is present in the 24E output folder before rerun; 24E validates required fields, resolves each artifact path, computes each artifact hash, and can allow 24F only if all required rows are filled, all referenced artifacts exist, each declared hash matches the referenced artifact, and no forbidden approval/execution field is true.

24E does not execute source recovery and does not approve source recovery.

## Current boundary

24E must not execute, enable, prepare, approve, or finalize:

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

`FX_OUTPUTS/gold_v2_24d_source_recovery_gap_resolution_plan_audit_only`

Required 24D files:

| role | file | expected |
| --- | --- | --- |
| 24D report | `GOLD_V2_24D_SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_AUDIT_ONLY_REPORT.md` | exists |
| 24D summary | `gold_v2_24d_source_recovery_gap_resolution_plan_summary.json` | exists and status matches expected |
| 24D input audit | `gold_v2_24d_input_audit.csv` | exists and reports no missing required input |
| 24D gap resolution plan | `gold_v2_24d_gap_resolution_plan.csv` | exists and has 3 plan rows |
| 24D artifact request template | `gold_v2_24d_artifact_request_template.csv` | exists and has 3 template rows |
| 24D integrated checks | `gold_v2_24d_integrated_checks.csv` | exists and has zero STOP rows |
| 24D required next gates | `gold_v2_24d_required_next_gates.csv` | exists and allows only 24E |
| 24D safety matrix | `gold_v2_24d_safety_matrix.csv` | exists and has zero STOP rows |

Optional 24E user/operator input file:

`FX_OUTPUTS/gold_v2_24e_source_recovery_artifact_list_intake_audit_only/gold_v2_24e_artifact_list_input.csv`

Expected 24D status:

`SOURCE_RECOVERY_GAP_RESOLUTION_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24e_source_recovery_artifact_list_intake_audit_only`

Required output files from one script run:

| role | file | expected |
| --- | --- | --- |
| input audit | `gold_v2_24e_input_audit.csv` | required 24D rows plus optional input status |
| artifact list template | `gold_v2_24e_artifact_list_input_template.csv` | fillable template copied from 24D request template |
| artifact list intake result | `gold_v2_24e_artifact_list_intake_result.csv` | one row per template/input row, including resolved path and hash verification |
| integrated checks | `gold_v2_24e_integrated_checks.csv` | PASS/STOP rows for 24D and artifact intake boundary |
| safety matrix | `gold_v2_24e_safety_matrix.csv` | confirms all forbidden actions remain false |
| required next gates | `gold_v2_24e_required_next_gates.csv` | allows only wait-for-artifact-list in template/incomplete mode or 24F after valid input plus hash verification |
| summary JSON | `gold_v2_24e_source_recovery_artifact_list_intake_summary.json` | machine-readable status and outputs |
| report | `GOLD_V2_24E_SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_AUDIT_ONLY_REPORT.md` | human-readable report |

## Expected counts

| item | expected count |
| --- | ---: |
| required 24D input artifacts | 8 |
| template rows | 3 |
| required artifact rows | 3 |
| source recovery executions | 0 |
| source recovery approvals granted | 0 |
| source identity finalizations/recoveries | 0 |
| AI API calls | 0 |
| Discord sends | 0 |
| MT5 orders | 0 |
| live hook calls | 0 |

## Validation rules for filled artifact list

24E requires exactly one filled row for each template `intake_id`.

For every row, these fields must be non-blank:

- `artifact_path`
- `artifact_hash`
- `artifact_role`
- `source_identity_scope`
- `upstream_sot_reference`

For `old_gold_disc8_quarantine_evidence`, `quarantine_note` must also be non-blank.

The following fields must be false if present:

- `execution_approved`
- `source_recovery_approved`

For every supplied row, 24E now hardens the intake by resolving `artifact_path` and verifying `artifact_hash` against the actual referenced artifact.

Accepted hash forms:

- SHA256 of the referenced file bytes
- Git blob SHA-1 of the referenced file bytes, for repo-tracked text artifacts where a GitHub blob SHA is used

Relative `artifact_path` values are resolved defensively against:

- the repository root
- the repository parent/Files folder
- `FX_OUTPUTS`
- the current working directory

If the artifact path does not exist, or the declared hash does not match either computed hash, the row is invalid and 24F remains blocked.

24E still does not verify semantic correctness of the artifact contents. Future review must still check whether the referenced artifact actually satisfies the evidence role. 24E only verifies structure, existence, and hash identity.

## Success statuses

Template/wait mode or incomplete/invalid supplied-list mode:

`SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_TEMPLATE_READY_AUDIT_ONLY_ARTIFACT_LIST_NOT_SUPPLIED_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

Validated-input mode:

`SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Stop conditions

The script must stop with non-zero exit code and write STOP outputs if any required source-of-truth or boundary check fails, including:

- missing 24D artifact
- unexpected 24D status
- upstream STOP rows present
- any recovery/finalization/live/final/external flag is true
- any forbidden gate is allowed
- 24D input audit reports missing required input
- 24D required next gate is not exactly 24E
- 24D template row count is not 3
- supplied 24E artifact list has duplicate or unknown intake IDs
- supplied 24E artifact list has forbidden approval/execution fields true

Blank artifact input, missing artifact path, incomplete required fields, or hash mismatch are not STOP conditions by themselves. They are wait/incomplete conditions and must not allow 24F.

## Required future explicit values

24E does not grant these values. It only records that they would be required later.

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

- `docs/gold_v2/GOLD_V2_24E_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`
- `docs/gold_v2/GOLD_V2_24E_SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_AUDIT_SPEC_20260606.md`
- `scripts/gold_v2_runtime/audit_gold_v2_24e_source_recovery_artifact_list_intake.py`
- `scripts/gold_v2_runtime/bat/24E_SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE.bat`

Output files:

- `FX_OUTPUTS/gold_v2_24e_source_recovery_artifact_list_intake_audit_only/GOLD_V2_24E_SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_AUDIT_ONLY_REPORT.md`
- `FX_OUTPUTS/gold_v2_24e_source_recovery_artifact_list_intake_audit_only/gold_v2_24e_source_recovery_artifact_list_intake_summary.json`
- `FX_OUTPUTS/gold_v2_24e_source_recovery_artifact_list_intake_audit_only/gold_v2_24e_input_audit.csv`
- `FX_OUTPUTS/gold_v2_24e_source_recovery_artifact_list_intake_audit_only/gold_v2_24e_artifact_list_input_template.csv`
- `FX_OUTPUTS/gold_v2_24e_source_recovery_artifact_list_intake_audit_only/gold_v2_24e_artifact_list_intake_result.csv`
- `FX_OUTPUTS/gold_v2_24e_source_recovery_artifact_list_intake_audit_only/gold_v2_24e_integrated_checks.csv`
- `FX_OUTPUTS/gold_v2_24e_source_recovery_artifact_list_intake_audit_only/gold_v2_24e_required_next_gates.csv`
- `FX_OUTPUTS/gold_v2_24e_source_recovery_artifact_list_intake_audit_only/gold_v2_24e_safety_matrix.csv`

## BAT execution order

Run only after 24D outputs already exist and have been reviewed:

1. `scripts\gold_v2_runtime\bat\24E_SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE.bat`

Do not run 24F automatically in the same step.

## What 24E implements

24E implements one integrated audit-only script that:

- loads 24D artifacts
- writes a fillable artifact list template
- optionally validates a supplied artifact list input CSV
- resolves referenced artifact paths
- computes SHA256 and Git blob SHA-1 for existing referenced artifacts
- blocks 24F unless all three supplied artifact rows are complete, existing, hash-matched, and approval/execution flags remain false
- writes input audit, integrated checks, safety matrix, required gates, summary JSON, and Markdown report

## What 24E does not implement

24E does not implement:

- source recovery execution
- source recovery approval
- source identity finalization
- semantic artifact evidence acceptance beyond intake/existence/hash verification
- live evaluator
- live hook
- final signal
- Discord notification
- MT5 order
- AI API review
- OHLC replay
- strategy/trade evaluation
