# GOLD V2 24F source recovery artifact list review audit-only spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `24F_SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_AUDIT_ONLY`
Mode: audit-only

## Purpose

24F reviews the 3 artifact references that passed 24E hardened intake.

24E hardened verifies structure, artifact existence, and hash identity. 24F performs the next audit-only review layer:

- verifies 24E hardened status and required next gate
- verifies all three 24E intake rows are hash-verified
- verifies the three expected evidence categories are present exactly once
- performs lightweight category-specific content/metadata checks
- records whether the artifact list is reviewable for later human/audit routing

24F does not execute source recovery and does not approve source recovery.

## Boundary

24F must not execute, enable, prepare, approve, or finalize:

- source recovery execution
- source recovery approval
- source identity finalization
- source identity recovery
- live evaluator
- live hook
- final signal
- Discord notification
- MT5 order
- AI API call
- OHLC replay/reconstruction
- approximate reimplementation

Old GOLD/DISC8 remain quarantined.

NO_SIGNAL must not send Discord.

## Inputs

Source-of-truth input folder:

`FX_OUTPUTS/gold_v2_24e_source_recovery_artifact_list_intake_audit_only`

Required 24E files:

| role | file | expected |
| --- | --- | --- |
| 24E report | `GOLD_V2_24E_SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_AUDIT_ONLY_REPORT.md` | exists |
| 24E summary | `gold_v2_24e_source_recovery_artifact_list_intake_summary.json` | status is `SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED` |
| 24E input audit | `gold_v2_24e_input_audit.csv` | exists and required inputs present |
| 24E artifact list input | `gold_v2_24e_artifact_list_input.csv` | exists |
| 24E artifact list intake result | `gold_v2_24e_artifact_list_intake_result.csv` | 3 rows, all `VALID_FOR_24F_AUDIT_ONLY_REVIEW_HASH_VERIFIED` |
| 24E integrated checks | `gold_v2_24e_integrated_checks.csv` | zero STOP rows |
| 24E required next gates | `gold_v2_24e_required_next_gates.csv` | only `24F_SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_AUDIT_ONLY` allowed |
| 24E safety matrix | `gold_v2_24e_safety_matrix.csv` | zero STOP rows |

## Expected artifact categories

Exactly one row must exist for each category:

- `source_identity_lineage_docs`
- `candidate_source_files`
- `old_gold_disc8_quarantine_evidence`

## Category review rules

### `source_identity_lineage_docs`

The referenced artifact should be a document or script that contains source identity lineage evidence. 24F checks for source-identity terms such as:

- `source identity`
- `source_row_hash`
- `source rows`
- `dry-run`
- `audit-only`

### `candidate_source_files`

The referenced artifact should be an existing source file, usually CSV. 24F checks:

- file exists and hash identity already passed in 24E
- if CSV, row count is greater than zero
- expected Tier2/source columns are present when possible, for example `entry_time`, `direction`, `strategy_id`, `tier2_key`, `cluster_id`, `top_candidate_id`, or `source_row_hash`

24F does not reconstruct trades, does not replay OHLC, and does not execute recovery.

### `old_gold_disc8_quarantine_evidence`

The referenced artifact should contain quarantine evidence for old GOLD/DISC8, including terms such as:

- `old GOLD`
- `DISC8`
- `quarantine`
- `HTF`
- `open-time`
- `confirmed`
- `source of truth`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24f_source_recovery_artifact_list_review_audit_only`

Required outputs:

| output | purpose |
| --- | --- |
| `gold_v2_24f_input_audit.csv` | required 24E input file existence |
| `gold_v2_24f_artifact_reference_review.csv` | one reviewed row per 24E artifact row |
| `gold_v2_24f_artifact_content_review_checks.csv` | category-specific checks |
| `gold_v2_24f_integrated_checks.csv` | upstream and 24F boundary checks |
| `gold_v2_24f_required_next_gates.csv` | audit-only next-step gates; all forbidden actions blocked |
| `gold_v2_24f_safety_matrix.csv` | safety gates and external action proof |
| `gold_v2_24f_source_recovery_artifact_list_review_summary.json` | machine summary |
| `GOLD_V2_24F_SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_AUDIT_ONLY_REPORT.md` | human report |

## Success status

If all 24E upstream checks pass and all three artifact rows are reviewable:

`SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

If 24E is valid but one or more artifact content/category reviews need more evidence:

`SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_REQUEST_MORE_EVIDENCE_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

If required 24E files or safety gates fail:

`24F_STOP_SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_INPUTS_OR_SAFETY`

## Next step policy

24F itself does not allow source recovery execution.

Possible audit-only next step after pass:

`24G_SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_AUDIT_ONLY`

This next step may present decision options only. It still must not execute recovery, finalize identity, enable live, send Discord, place MT5 orders, call AI APIs, or enable live hooks.

## Non-actions

24F does not implement:

- source recovery execution
- source recovery approval
- source identity finalization
- source identity recovery
- semantic acceptance as final source-of-truth
- live evaluator
- final signal
- Discord notification
- MT5 order
- AI API call
- live hook
- OHLC replay
- strategy/trade evaluation
