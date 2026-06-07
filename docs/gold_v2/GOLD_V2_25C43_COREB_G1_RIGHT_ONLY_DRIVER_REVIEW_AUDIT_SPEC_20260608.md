# GOLD V2 25C43 CoreB G1 right_only driver review audit spec

Date: 2026-06-08
Step: `25C43_COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_AUDIT_ONLY`
Mode: audit-only driver review

## Purpose

25C43 reads the reconciled 25C42 row-level `right_only` export and classifies the right_only rows into review drivers.

25C43 does not create a new bundle, does not run a dry-run, does not change rules, and does not approve any CoreB variant. It only describes where the target-damaging right_only rows are concentrated and what route should be planned next.

## 25C42 source-of-truth context

25C42 completed successfully:

```text
status=COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_COMPLETED_AUDIT_ONLY_DRIVER_REVIEW_READY
reconciliation_passed=true
right_only_row_count=672
next_recommended_step=25C43_COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_AUDIT_ONLY
```

The exported rows contain:

```text
variant
dataset
entry_time
policy
_merge
baseline_merge
```

A row where:

```text
_merge == right_only
baseline_merge == both
```

means the adjusted variant removed a row that matched the target under baseline. This is classified as incremental right_only damage.

A row where:

```text
_merge == right_only
baseline_merge == right_only
```

was already target-only under baseline and is not caused by adjusted narrowing.

## Required inputs

All inputs are read from:

```text
FX_OUTPUTS/gold_v2_25c42_coreb_g1_right_only_row_level_export_audit_only/
```

Required files:

```text
02_25c42_coreb_g1_right_only_row_level_export_summary.json
05_25c42_variant_right_only_row_level_compare_rows.csv
06_25c42_right_only_by_variant_dataset_policy.csv
07_25c42_right_only_export_reconciliation_matrix.csv
09_25c42_acceptance_gate_matrix.csv
10_25c42_next_step_plan.csv
```

## Review outputs

Output directory:

```text
FX_OUTPUTS/gold_v2_25c43_coreb_g1_right_only_driver_review_audit_only/
```

Expected outputs:

```text
00_不要_25c43_file_request_list.csv
01_25c43_GOLD_V2_COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_AUDIT_ONLY_REPORT.md
02_25c43_coreb_g1_right_only_driver_review_summary.json
03_25c43_input_audit.csv
04_25c43_right_only_driver_classification_matrix.csv
05_25c43_incremental_damage_by_variant_dataset_policy.csv
06_25c43_right_only_variant_overlap_matrix.csv
07_25c43_incremental_damage_monthly_concentration_matrix.csv
08_25c43_driver_review_findings_matrix.csv
09_25c43_execution_boundary_matrix.csv
10_25c43_acceptance_gate_matrix.csv
11_25c43_next_step_plan.csv
```

## Expected review logic

25C43 should compute:

```text
persistent_baseline_right_only = baseline_merge == right_only
incremental_damage_from_baseline_both = baseline_merge == both
unknown_baseline_driver = any other baseline_merge
```

It should then compare variants:

```text
A003 damage should be highest.
A001 should be lower than A003 but higher than A002/A004.
A002 and A004 should be identical on aggregate and right_only set overlap.
```

These are review findings only, not adoption recommendations.

## Non-goals / hard stops

```text
No source recovery.
No source mutation.
No rule condition change.
No new dry-run.
No new row-level export.
No new variant search.
No A003 approval.
No CoreB live evaluator unblock.
No final signal.
No Discord notification.
No MT5 order.
No AI API call.
No live hook.
NO_SIGNAL must not notify Discord.
Old GOLD / DISC8 remains quarantined.
```

## Expected status

```text
COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_COMPLETED_AUDIT_ONLY_NEXT_PLAN_REQUIRED
```

## Stop statuses

```text
25C43_STOP_MISSING_INPUT_AUDIT_ONLY
25C43_STOP_25C42_CONTRACT_UNSAFE_AUDIT_ONLY
```

## Next-step policy

If the review completes, the next recommended step should be a plan-only step, for example:

```text
25C44_COREB_G1_RIGHT_ONLY_DAMAGE_ROUTE_PLAN_AUDIT_ONLY
```

25C44 may decide whether to stop, plan retention around target-damaging rows, or design a later accepted dry-run. 25C44 must still not run a dry-run or unblock live behavior.
