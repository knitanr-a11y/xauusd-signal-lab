# GOLD V2 25C52 dry-run source candidate review implementation note

Date: 2026-06-08

Repo: `knitanr-a11y/xauusd-signal-lab`

## Implemented step

```text
25C52_COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY
```

Mode: audit-only source candidate review / binding package.

## What was implemented

Added a repository-backed audit-only Python script and BAT launcher for 25C52.

```text
scripts/gold_v2_runtime/audit_gold_v2_25c52_coreb_g1_dry_run_source_candidate_review_audit_only.py
scripts/gold_v2_runtime/bat/25C52_COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY.bat
```

The BAT keeps the command window open with `pause` on both success and STOP/error paths.

## Input files

25C52 reads from:

```text
FX_OUTPUTS/gold_v2_25c51_coreb_g1_dry_run_source_concretion_review_audit_only/
```

Required files:

```text
02_25c51_dry_run_source_concretion_review_summary.json
04_25c51_contract_audit.csv
06_25c51_source_candidate_matrix.csv
07_25c51_source_selection_matrix.csv
08_25c51_execution_boundary_matrix.csv
09_25c51_gates.csv
10_25c51_next_step_plan.csv
11_25c51_handoff_notes.csv
```

## Candidate expected from 25C51

```text
gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv
```

## Output directory

```text
FX_OUTPUTS/gold_v2_25c52_coreb_g1_dry_run_source_candidate_review_audit_only/
```

Expected outputs:

```text
00_不要_25c52_file_request_list.csv
01_25c52_GOLD_V2_COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md
02_25c52_dry_run_source_candidate_review_summary.json
03_25c52_input_audit.csv
04_25c52_contract_audit.csv
05_25c52_candidate_file_metadata.csv
06_25c52_candidate_header_review.csv
07_25c52_source_binding_matrix.csv
08_25c52_execution_boundary_matrix.csv
09_25c52_gates.csv
10_25c52_next_step_plan.csv
11_25c52_handoff_notes.csv
```

## Review behavior

25C52 checks:

```text
top candidate path matches 25C51 selection
candidate file exists locally
candidate extension is .csv
candidate is non-empty
candidate header is readable
candidate is under FX_OUTPUTS
```

If those checks pass, the candidate can be bound only for future audit planning:

```text
source_binding_status = SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY
source_confirmed_for_execution = false
future_dry_run_execution_allowed = false
```

## Success status

```text
COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_READY_AUDIT_ONLY_SOURCE_BOUND_FOR_PLANNING_EXECUTION_BLOCKED
```

## Stop conditions

```text
25C52_STOP_MISSING_INPUT_AUDIT_ONLY
25C52_STOP_25C51_CONTRACT_UNSAFE_AUDIT_ONLY
25C52_STOP_SOURCE_CANDIDATE_UNSAFE_AUDIT_ONLY
```

## Run order

From the repository root:

```bat
scripts\gold_v2_runtime\bat\25C52_COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY.bat
```

Or:

```bat
python scripts\gold_v2_runtime\audit_gold_v2_25c52_coreb_g1_dry_run_source_candidate_review_audit_only.py
```

## Next step

25C52 may recommend only this next audit-only preflight specification step:

```text
25C53_COREB_G1_DRY_RUN_PREFLIGHT_SPEC_AUDIT_ONLY
```

25C53 must still be audit-only and must not execute dry-run unless a later explicit instruction changes the boundary.

## Explicit boundaries

25C52 does not confirm a source for execution, approve A002/A004 or any variant, execute replay, execute dry-run, change conditions, change sources, recover sources, run live paths, call AI API, notify Discord, place MT5 orders, run live hooks, or create final signals.

NO_SIGNAL Discord notification remains disabled.
