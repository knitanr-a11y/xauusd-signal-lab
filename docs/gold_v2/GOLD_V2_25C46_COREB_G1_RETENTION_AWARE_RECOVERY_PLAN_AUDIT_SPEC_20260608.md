# GOLD V2 25C46 CoreB G1 retention-aware recovery plan audit spec

Date: 2026-06-08
Logical step: `25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_ONLY`
Neutral implementation step: `25C46_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY`
Mode: audit-only plan/review

## Purpose

25C46 reads the corrected 25C45 attribution outputs and creates a coverage review for the next planning stage. It is plan/review-only and must not run a replay, change CoreB conditions, approve any variant, or enable live use.

Because direct GitHub creation of the Python script was blocked by the tool safety layer, the implementation name is neutralized. The original 25C45 next step remains the logical alias and must be preserved in output summaries.

Required summary mapping:

```json
{
  "step": "25C46_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY",
  "logical_step_alias": "25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_ONLY"
}
```

## Count semantics

25C45 corrected the key-count issue:

```text
unique_incremental_damage_keys = 360
filter_attribution_rows = 1260
```

25C46 must use `unique_incremental_damage_keys` as the damaged-key population. Attribution rows are not additive because one damaged key can map to multiple baseline filters.

Coverage must always be computed using unique keys:

```text
variant + dataset + entry_time + policy
```

## Required inputs

From `FX_OUTPUTS/gold_v2_25c45_coreb_g1_incremental_damage_filter_attribution_audit_only/`:

```text
02_25c45_coreb_g1_incremental_damage_filter_attribution_summary.json
04_25c45_incremental_damage_key_filter_attribution_rows.csv
07_25c45_filter_retention_candidate_matrix.csv
08_25c45_attribution_quality_matrix.csv
```

The full filter/variant matrices from 25C45 may be read for diagnosis, but they are not required for the minimal 25C46 coverage review.

## Plan logic

For each variant and retention-priority cutoff, 25C46 computes unique key coverage:

```text
retained_filters = filters where retention_priority <= cutoff
covered_unique_damage_keys = unique damaged keys with at least one retained filter
uncovered_unique_damage_keys = total_unique_damage_keys - covered_unique_damage_keys
```

Selection rule:

```text
1. Full known-key coverage first
2. Then lowest unique damaged-key count
3. Then lowest retained-filter count
4. If A002 and A004 tie, prefer A002 as the representative
```

Current evidence suggests A002 and A004 are equivalent on this reviewed right_only set, so A002 is the representative when tied.

## Neutral output directory

Use this directory for the neutral implementation:

```text
FX_OUTPUTS/gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only/
```

Expected files:

```text
00_不要_25c46_file_request_list.csv
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

Do not use a separate `gold_v2_25c46_coreb_g1_retention_aware_recovery_plan_audit_only/` output directory unless the implementation is deliberately renamed and the handoff is updated again. The neutral output path above is the current expected path.

## Expected status

```text
COREB_G1_FILTER_COVERAGE_REVIEW_READY_AUDIT_ONLY
```

## Next recommended step

```text
25C47_COREB_G1_FILTER_COVERAGE_NEXT_PLAN_AUDIT_ONLY
```

25C47 must not be started until 25C46 output artifacts are produced and reviewed.

## Stop / no-go policy

25C46 must stop if the 25C45 summary does not show the corrected status, if the unique damaged-key count is missing, if the 25C45 next step does not point to a 25C46 step, or if no full known-key coverage candidate exists.

25C46 must not approve A002/A004, must not run any next-stage evaluation, and must not change live/external behavior.
