# GOLD V2 24E artifact candidate prefill audit-only spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `24E_ARTIFACT_CANDIDATE_PREFILL_AUDIT_ONLY`
Mode: audit-only

## Purpose

This step scans already-existing repository and `FX_OUTPUTS` artifacts that may satisfy the 3 unresolved 24E artifact-list rows.

It exists to avoid hand-written evidence fabrication.

It does not create or overwrite `gold_v2_24e_artifact_list_input.csv`.

Instead, it writes a separate candidate file:

`gold_v2_24e_artifact_list_input_candidate_prefill_DO_NOT_USE_UNREVIEWED.csv`

The candidate file is only a draft manifest. It must be reviewed by the user/operator and then copied manually to `gold_v2_24e_artifact_list_input.csv` only if every row is acceptable.

After that, 24E hardened intake must be rerun. 24E hardened remains the gatekeeper and verifies actual artifact existence/hash before 24F can be allowed.

## Boundary

This step must not:

- execute source recovery
- approve source recovery
- finalize or recover source identity
- create new evidence to satisfy a gap
- overwrite the real 24E input file
- enable live evaluator or live hook
- produce final signal
- send Discord
- place MT5 orders
- call AI APIs
- use old GOLD/DISC8 as active source-of-truth
- approximate-reimplement source logic

Old GOLD/DISC8 remain quarantined.

## Inputs

Preferred template input:

`FX_OUTPUTS/gold_v2_24e_source_recovery_artifact_list_intake_audit_only/gold_v2_24e_artifact_list_input_template.csv`

Fallback template input:

`FX_OUTPUTS/gold_v2_24d_source_recovery_gap_resolution_plan_audit_only/gold_v2_24d_artifact_request_template.csv`

Expected template rows: 3.

## Candidate artifact categories

The script searches candidates for each 24E category:

| category | intended artifact type |
| --- | --- |
| `source_identity_lineage_docs` | existing docs/scripts that describe source identity lineage and source row/hash handling |
| `candidate_source_files` | existing `FX_OUTPUTS` source CSV/JSON files, especially Tier2 source rows/reconciled source rows |
| `old_gold_disc8_quarantine_evidence` | existing docs that prove old GOLD/DISC8 quarantine and HTF open-time mismatch concern |

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24e_artifact_candidate_prefill_audit_only`

Required outputs:

| output | purpose |
| --- | --- |
| `gold_v2_24e_artifact_candidate_inventory.csv` | all known and discovered candidate artifacts with existence/hash metadata |
| `gold_v2_24e_artifact_candidate_prefill_review_matrix.csv` | selected best candidate per intake row plus review status |
| `gold_v2_24e_artifact_list_input_candidate_prefill_DO_NOT_USE_UNREVIEWED.csv` | copy-ready draft candidate manifest, not the real 24E input |
| `gold_v2_24e_artifact_candidate_prefill_summary.json` | machine summary |
| `GOLD_V2_24E_ARTIFACT_CANDIDATE_PREFILL_AUDIT_ONLY_REPORT.md` | human report |

## Success logic

This step has no authority to allow 24F.

It can only report whether a candidate prefill draft was created with one existing hash-computed artifact for each 24E row.

Even if this step finds all 3 rows, 24F remains blocked until:

1. the user/operator reviews the draft candidate manifest,
2. the draft is copied to `gold_v2_24e_artifact_list_input.csv`,
3. `24E_SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE.bat` is rerun,
4. 24E hardened produces `SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`, and
5. 24E hardened required next gates allow only `24F_SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_AUDIT_ONLY`.

## Hash policy

For every existing artifact, the script computes:

- SHA256
- Git blob SHA-1

The candidate prefill uses SHA256 by default.

24E hardened later accepts either SHA256 or Git blob SHA-1, but this prefill step prefers SHA256 because it is independent of Git storage format.

## Final status values

Possible statuses:

- `24E_ARTIFACT_CANDIDATE_PREFILL_READY_AUDIT_ONLY_REVIEW_REQUIRED`
- `24E_ARTIFACT_CANDIDATE_PREFILL_INCOMPLETE_AUDIT_ONLY_MISSING_EXISTING_ARTIFACTS`
- `24E_ARTIFACT_CANDIDATE_PREFILL_STOP_TEMPLATE_MISSING_OR_INVALID`

No status from this step grants source recovery, source identity finalization, live use, final signal, Discord, MT5, AI API, live hook, or 24F.
