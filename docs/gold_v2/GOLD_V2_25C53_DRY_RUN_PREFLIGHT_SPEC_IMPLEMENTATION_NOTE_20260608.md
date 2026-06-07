# GOLD V2 25C53 dry-run preflight spec implementation note

Date: 2026-06-08

Repo: `knitanr-a11y/xauusd-signal-lab`

## Implemented step

```text
25C53_COREB_G1_DRY_RUN_PREFLIGHT_SPEC_AUDIT_ONLY
```

Mode: audit-only dry-run preflight specification.

## What was implemented

Added a repository-backed audit-only Python script and BAT launcher for 25C53.

```text
scripts/gold_v2_runtime/audit_gold_v2_25c53_coreb_g1_dry_run_preflight_spec_audit_only.py
scripts/gold_v2_runtime/bat/25C53_COREB_G1_DRY_RUN_PREFLIGHT_SPEC_AUDIT_ONLY.bat
```

The BAT keeps the command window open with `pause` on both success and STOP/error paths.

## Input files

25C53 reads from:

```text
FX_OUTPUTS/gold_v2_25c52_coreb_g1_dry_run_source_candidate_review_audit_only/
```

Required files:

```text
02_25c52_dry_run_source_candidate_review_summary.json
04_25c52_contract_audit.csv
05_25c52_candidate_file_metadata.csv
06_25c52_candidate_header_review.csv
07_25c52_source_binding_matrix.csv
08_25c52_execution_boundary_matrix.csv
09_25c52_gates.csv
10_25c52_next_step_plan.csv
11_25c52_handoff_notes.csv
```

## Candidate source carried forward

```text
gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv
```

The candidate remains planning-only:

```text
source_binding_status = SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY
source_confirmed_for_execution = false
future_dry_run_execution_allowed = false
```

## Expected header columns

```text
dataset
entry_time
policy
filter
source_count_by_entry_time
unique_origin_count_by_entry_time
same_count_threshold
unique_origins_threshold
intersection_only
full_coreb_parity
```

## Output directory

```text
FX_OUTPUTS/gold_v2_25c53_coreb_g1_dry_run_preflight_spec_audit_only/
```

Expected outputs:

```text
00_不要_25c53_file_request_list.csv
01_25c53_GOLD_V2_COREB_G1_DRY_RUN_PREFLIGHT_SPEC_AUDIT_ONLY_REPORT.md
02_25c53_dry_run_preflight_spec_summary.json
03_25c53_input_audit.csv
04_25c53_contract_audit.csv
05_25c53_preflight_input_matrix.csv
06_25c53_preflight_check_matrix.csv
07_25c53_preflight_output_spec_matrix.csv
08_25c53_execution_boundary_matrix.csv
09_25c53_gates.csv
10_25c53_next_step_plan.csv
11_25c53_handoff_notes.csv
```

## Success status

```text
COREB_G1_DRY_RUN_PREFLIGHT_SPEC_READY_AUDIT_ONLY_EXECUTION_GATE_REVIEW_REQUIRED
```

## Stop conditions

```text
25C53_STOP_MISSING_INPUT_AUDIT_ONLY
25C53_STOP_25C52_CONTRACT_UNSAFE_AUDIT_ONLY
25C53_STOP_PREFLIGHT_SPEC_UNSAFE_AUDIT_ONLY
```

## Run order

From the repository root:

```bat
scripts\gold_v2_runtime\bat\25C53_COREB_G1_DRY_RUN_PREFLIGHT_SPEC_AUDIT_ONLY.bat
```

Or:

```bat
python scripts\gold_v2_runtime\audit_gold_v2_25c53_coreb_g1_dry_run_preflight_spec_audit_only.py
```

## Next step

25C53 may recommend only this next audit-only execution gate review step:

```text
25C54_COREB_G1_DRY_RUN_EXECUTION_GATE_REVIEW_AUDIT_ONLY
```

25C54 must remain audit-only unless a later explicit instruction changes the boundary.

## Explicit boundaries

25C53 does not confirm source for execution, approve A002/A004 or any variant, execute replay, execute dry-run, change conditions, change sources, recover sources, run live paths, call AI API, notify Discord, place MT5 orders, run live hooks, or create final signals.

NO_SIGNAL Discord notification remains disabled.
