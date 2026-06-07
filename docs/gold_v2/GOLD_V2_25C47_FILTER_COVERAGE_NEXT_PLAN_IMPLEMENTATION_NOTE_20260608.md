# GOLD V2 25C47 filter coverage next plan implementation note

Date: 2026-06-08

Repo: `knitanr-a11y/xauusd-signal-lab`

## Implemented step

```text
25C47_COREB_G1_FILTER_COVERAGE_NEXT_PLAN_AUDIT_ONLY
```

Mode: audit-only next-plan review.

## What was implemented

Added a repository-backed audit-only Python script and BAT launcher for 25C47.

```text
scripts/gold_v2_runtime/audit_gold_v2_25c47_coreb_g1_filter_coverage_next_plan_audit_only.py
scripts/gold_v2_runtime/bat/25C47_COREB_G1_FILTER_COVERAGE_NEXT_PLAN_AUDIT_ONLY.bat
```

The BAT keeps the command window open with `pause` on both success and STOP/error paths.

## Input files

25C47 reads from:

```text
FX_OUTPUTS/gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only/
```

Required files:

```text
02_25c46_filter_coverage_review_summary.json
04_25c46_coverage_matrix.csv
05_25c46_selected_coverage_plan.csv
07_25c46_limits.csv
08_25c46_gates.csv
09_25c46_next_step_plan.csv
```

## Output directory

```text
FX_OUTPUTS/gold_v2_25c47_coreb_g1_filter_coverage_next_plan_audit_only/
```

Expected outputs:

```text
00_不要_25c47_file_request_list.csv
01_25c47_GOLD_V2_COREB_G1_FILTER_COVERAGE_NEXT_PLAN_AUDIT_ONLY_REPORT.md
02_25c47_filter_coverage_next_plan_summary.json
03_25c47_input_audit.csv
04_25c47_contract_audit.csv
05_25c47_representative_candidate_review.csv
06_25c47_next_option_matrix.csv
07_25c47_execution_boundary_matrix.csv
08_25c47_gates.csv
09_25c47_next_step_plan.csv
10_25c47_handoff_notes.csv
```

## Contract checked from 25C46

The script validates the 25C46 step, alias, status, key counts, coverage counts, selected representative candidate, and safety flags.

Important 25C46 source-of-truth facts:

```text
known_unique_damage_keys = 360
filter_attribution_rows = 1260
coverage_rows = 11
full_coverage_candidate_rows = 7
selected_variant_code = A002
selected_retention_priority_cutoff = 1
selected_total_unique_damage_keys = 69
selected_covered_unique_keys = 69
selected_open_unique_keys = 0
selected_retained_filter_count = 2
selected_approval_status = NOT_APPROVED_REVIEW_ONLY
a002_a004_approval_status = NOT_APPROVED_REVIEW_ONLY
```

## Success conditions

25C47 succeeds only if:

```text
required 25C46 files exist
25C46 summary contract matches
25C46 coverage and selected plan row counts match summary
25C46 limits have no STOP
25C46 gate keeps 25C47 blocked until artifact review
there is exactly one selected representative
selected representative remains A002 with NOT_APPROVED_REVIEW_ONLY
all execution and external action flags remain false
```

Successful status:

```text
COREB_G1_FILTER_COVERAGE_NEXT_PLAN_READY_AUDIT_ONLY
```

## Stop conditions

```text
25C47_STOP_MISSING_INPUT_AUDIT_ONLY
25C47_STOP_25C46_CONTRACT_UNSAFE_AUDIT_ONLY
25C47_STOP_REPRESENTATIVE_CANDIDATE_UNSAFE_AUDIT_ONLY
```

## Run order

From the repository root:

```bat
scripts\gold_v2_runtime\bat\25C47_COREB_G1_FILTER_COVERAGE_NEXT_PLAN_AUDIT_ONLY.bat
```

Or:

```bat
python scripts\gold_v2_runtime\audit_gold_v2_25c47_coreb_g1_filter_coverage_next_plan_audit_only.py
```

## Next step

25C47 may recommend only this next specification/review step:

```text
25C48_COREB_G1_REPRESENTATIVE_FILTER_SET_REVIEW_SPEC_AUDIT_ONLY
```

## Explicit boundaries

25C47 does not approve A002/A004 or any variant.

25C47 does not execute replay, dry-run, condition changes, source changes, source recovery, live paths, AI API calls, Discord notifications, MT5 orders, live hooks, or final signals.

NO_SIGNAL Discord notification remains disabled.
