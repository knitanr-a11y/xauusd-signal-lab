# GOLD V2 25C46 filter coverage review local runbook

Date: 2026-06-08

This note preserves the 25C46 continuity without changing the already completed 25C45 outputs.

## Name mapping

Logical name from 25C45:

```text
25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_ONLY
```

Neutral implementation name:

```text
25C46_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY
```

The neutral implementation must write the logical name into `logical_step_alias` by reading `next_recommended_step` from the 25C45 summary. This prevents later mismatch.

## Input facts from corrected 25C45

```text
unique_incremental_damage_keys = 360
filter_attribution_rows = 1260
unique_cleanly_attributed_damage_keys = 360
unique_not_cleanly_attributed_damage_keys = 0
```

## Required behavior

1. Read 25C45 summary, attribution rows, retention candidates, and quality matrix.
2. Validate that 25C45 completed and points to a 25C46 step.
3. For each variant and retention priority cutoff, compute coverage by unique key:

```text
variant + dataset + entry_time + policy
```

4. Select the full-coverage row with:

```text
lowest unique key count
then lowest filter count
then A002 before A004 when tied
```

5. Write `logical_step_alias` into the summary.
6. Do not execute any next-stage evaluation in this step.

## Output directory

```text
FX_OUTPUTS/gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only/
```

## Expected outputs

```text
01_25c46_GOLD_V2_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY_REPORT.md
02_25c46_filter_coverage_review_summary.json
03_25c46_input_audit.csv
04_25c46_coverage_matrix.csv
05_25c46_selected_coverage_plan.csv
06_25c46_notes.csv
07_25c46_limits.csv
08_25c46_gates.csv
09_25c46_next_step_plan.csv
```

## Next step

```text
25C47_COREB_G1_FILTER_COVERAGE_NEXT_PLAN_AUDIT_ONLY
```

25C47 should remain a planning step unless separately accepted later.
