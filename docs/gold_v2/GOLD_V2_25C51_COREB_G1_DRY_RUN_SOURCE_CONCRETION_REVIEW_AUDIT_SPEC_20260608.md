# GOLD V2 25C51 CoreB G1 dry-run source concretion review audit spec

Date: 2026-06-08

Step: `25C51_COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_AUDIT_ONLY`

Mode: audit-only source concretion review

## Purpose

25C51 reads the 25C50 readiness review artifacts and scans audited local `FX_OUTPUTS` artifacts for candidate baseline replay signal source files. It prepares a candidate review package only.

25C51 must not run replay, must not run dry-run, must not approve A002/A004 or any variant, must not change sources or conditions, and must not enable live/external behavior.

## Required inputs

From:

```text
FX_OUTPUTS/gold_v2_25c50_coreb_g1_representative_dry_run_readiness_review_audit_only/
```

Required files:

```text
02_25c50_representative_dry_run_readiness_review_summary.json
04_25c50_contract_audit.csv
05_25c50_readiness_matrix.csv
06_25c50_unresolved_source_matrix.csv
07_25c50_execution_boundary_matrix.csv
08_25c50_gates.csv
09_25c50_next_step_plan.csv
10_25c50_handoff_notes.csv
```

## Source-of-truth facts from 25C50

25C51 must preserve these facts:

```text
step = 25C50_COREB_G1_REPRESENTATIVE_DRY_RUN_READINESS_REVIEW_AUDIT_ONLY
status = COREB_G1_REPRESENTATIVE_DRY_RUN_READINESS_REVIEW_READY_AUDIT_ONLY_SOURCE_CONCRETION_REQUIRED
audit_only = true
readiness_review_only = true
representative_variant_code = A002
representative_filters = same_count>=2&unique_origins>=2, unique_origins>=2
representative_approval_status = NOT_APPROVED_REVIEW_ONLY
dry_run_spec_ready_for_manual_review = true
source_concretion_required = true
exact_baseline_replay_signal_source_confirmed = false
future_dry_run_execution_allowed = false
next_recommended_step = 25C51_COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_AUDIT_ONLY
total_stop_rows = 0
```

All execution and external flags in the 25C50 summary must remain false.

## Candidate search rules

25C51 may scan only local audited artifacts under `FX_OUTPUTS` by default. It should generate a candidate matrix using path/name scoring only and must not read raw OHLC, must not reconstruct signals, and must not approximate exploration logic.

Default candidate scoring terms:

```text
25c10
replay
signal
rows
coreb
g1
baseline
```

Candidate review is not source approval. Even a high-scoring candidate remains `SOURCE_CANDIDATE_REVIEW_REQUIRED` until reviewed.

## Output directory

```text
FX_OUTPUTS/gold_v2_25c51_coreb_g1_dry_run_source_concretion_review_audit_only/
```

Expected files:

```text
00_不要_25c51_file_request_list.csv
01_25c51_GOLD_V2_COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_AUDIT_ONLY_REPORT.md
02_25c51_dry_run_source_concretion_review_summary.json
03_25c51_input_audit.csv
04_25c51_contract_audit.csv
05_25c51_source_search_spec_matrix.csv
06_25c51_source_candidate_matrix.csv
07_25c51_source_selection_matrix.csv
08_25c51_execution_boundary_matrix.csv
09_25c51_gates.csv
10_25c51_next_step_plan.csv
11_25c51_handoff_notes.csv
```

## Success status

```text
COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_READY_AUDIT_ONLY_SOURCE_CANDIDATE_REVIEW_REQUIRED
```

This status means source concretion review completed, but future dry-run execution is still blocked.

## Stop statuses

```text
25C51_STOP_MISSING_INPUT_AUDIT_ONLY
25C51_STOP_25C50_CONTRACT_UNSAFE_AUDIT_ONLY
25C51_STOP_SOURCE_SEARCH_UNSAFE_AUDIT_ONLY
```

## Next recommended step

25C51 may recommend only candidate review/binding specification, not execution:

```text
25C52_COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY
```

## Boundaries

25C51 must not approve variants, must not execute replay or dry-run, must not mutate sources or conditions, must not unblock live evaluator, must not send Discord notifications, must not place MT5 orders, must not call AI API, must not run live hooks, and must not create final signals.

NO_SIGNAL Discord notification remains disabled.
