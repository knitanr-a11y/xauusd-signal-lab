# GOLD V2 25C46 filter coverage review implementation note

Date: 2026-06-08

Repo: `knitanr-a11y/xauusd-signal-lab`

## Implemented step

```text
step = 25C46_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY
logical_step_alias = 25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_ONLY
```

The implementation uses the neutral step name and preserves the formal 25C45 next step as `logical_step_alias`.

## Files added

```text
scripts/gold_v2_runtime/audit_gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only.py
scripts/gold_v2_runtime/bat/25C46_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY.bat
```

## Inputs

The script reads the corrected 25C45 audit artifacts from:

```text
FX_OUTPUTS/gold_v2_25c45_coreb_g1_incremental_damage_filter_attribution_audit_only/
```

Required files:

```text
02_25c45_coreb_g1_incremental_damage_filter_attribution_summary.json
04_25c45_incremental_damage_key_filter_attribution_rows.csv
07_25c45_filter_retention_candidate_matrix.csv
08_25c45_attribution_quality_matrix.csv
```

## Outputs

The script writes to:

```text
FX_OUTPUTS/gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only/
```

Expected output files:

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

## Count contract

25C46 enforces the corrected 25C45 counts:

```text
unique_incremental_damage_keys = 360
filter_attribution_rows = 1260
unique_cleanly_attributed_damage_keys = 360
unique_not_cleanly_attributed_damage_keys = 0
```

The coverage population is the unique key count, not the attribution row count.

Coverage key:

```text
variant + dataset + entry_time + policy
```

## Review logic

For each variant and each `retention_priority` cutoff, the script calculates:

```text
total_unique_damage_keys
covered_unique_keys
open_unique_keys
coverage_rate_pct
retained_filter_count
```

Representative row selection:

```text
1. full known-key coverage
2. lowest unique damaged-key count
3. lowest retained-filter count
4. A002 before A004 when tied
```

The selected representative is not an approval decision.

## Run order

From the repository root:

```bat
scripts\gold_v2_runtime\bat\25C46_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY.bat
```

Or:

```bat
python scripts\gold_v2_runtime\audit_gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only.py
```

## Success conditions

The script succeeds only when the corrected 25C45 contract matches, the expected count semantics match, the attribution CSV unique-key count is 360, the attribution CSV row count is 1260, the quality matrix has no STOP row, retention candidates are present, and at least one full known-key coverage row exists.

Successful status:

```text
COREB_G1_FILTER_COVERAGE_REVIEW_READY_AUDIT_ONLY
```

## Stop conditions

The script stops safely on missing inputs, unsafe 25C45 contract, count mismatch, required-column mismatch, or no full known-key coverage row.

Stop statuses:

```text
25C46_STOP_MISSING_INPUT_AUDIT_ONLY
25C46_STOP_25C45_CONTRACT_UNSAFE_AUDIT_ONLY
25C46_STOP_NO_FULL_KNOWN_KEY_COVERAGE_AUDIT_ONLY
```

## Boundaries

This step is review/plan-only. It does not run any next-stage evaluation, does not change source artifacts or strategy conditions, does not approve A002/A004 or any other variant, and does not enable external or live behavior.

## Next step lock

The script writes:

```text
next_recommended_step = 25C47_COREB_G1_FILTER_COVERAGE_NEXT_PLAN_AUDIT_ONLY
requires_25c46_artifact_review_before_25c47 = true
```

25C47 remains blocked until the 25C46 output artifacts are produced and reviewed.
