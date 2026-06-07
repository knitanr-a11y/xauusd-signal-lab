# GOLD V2 25C42 CoreB G1 right_only row-level export audit spec

Date: 2026-06-08
Step: `25C42_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_AUDIT_ONLY`
Mode: audit-only row-level export

## Purpose

25C42 executes the row-level export approved after 25C41. It uses the exact CoreB G1 compare construction from 25C37 and writes full row-level compare rows plus `right_only`-only rows for A001-A004.

25C42 is still audit-only. It does not approve A003, does not unblock CoreB live evaluator, and does not create a final signal.

## Human acceptance

25C41 ended with:

```text
HUMAN_ACCEPT_25C41_BEFORE_25C42_RIGHT_ONLY_ROW_LEVEL_EXPORT
```

25C42 must require an explicit execution flag:

```text
--accept-25c42-row-level-export
```

The BAT for this step may include that flag only after human approval has been given.

## Source-of-truth lineage

25C42 must read the 25C41 export contract and the future source inputs defined there. It must not infer inputs from memory.

Required control inputs:

```text
FX_OUTPUTS/gold_v2_25c41_coreb_g1_right_only_row_level_export_plan_audit_only/02_25c41_coreb_g1_right_only_row_level_export_plan_summary.json
FX_OUTPUTS/gold_v2_25c41_coreb_g1_right_only_row_level_export_plan_audit_only/04_25c41_future_export_input_contract.csv
FX_OUTPUTS/gold_v2_25c41_coreb_g1_right_only_row_level_export_plan_audit_only/05_25c41_future_export_output_schema_contract.csv
FX_OUTPUTS/gold_v2_25c41_coreb_g1_right_only_row_level_export_plan_audit_only/06_25c41_future_export_reconciliation_contract.csv
FX_OUTPUTS/gold_v2_25c41_coreb_g1_right_only_row_level_export_plan_audit_only/08_25c41_acceptance_gate_matrix.csv
FX_OUTPUTS/gold_v2_25c41_coreb_g1_right_only_row_level_export_plan_audit_only/09_25c41_next_step_plan.csv
```

Future export inputs are read from `04_25c41_future_export_input_contract.csv` and are expected to include:

```text
25C36 summary
25C36 adjusted bundles
25C36 adjusted membership
25C10 filter replay rows
25C15 selected policy summary
25C7 target compare window summary
25B3 shortlist file audit
```

## Compare construction

Use the same key and compare structure as 25C37:

```text
KEY = dataset, entry_time, policy
```

For each variant:

```text
1. Read 25C10 filter replay signal rows.
2. Restrict to 25C15 selected output policies.
3. Read target `rr125_top_ledgers.csv` through the audited 25B3 file audit.
4. Restrict target by 25C7 feature_min_time/feature_max_time and selected policies.
5. Build target_key = distinct KEY.
6. Build replay_key = distinct KEY from baseline or narrowed replay.
7. Outer merge replay_key and target_key with indicator=True.
8. Export `_merge` as both / left_only / right_only.
```

Variant narrowing must use only the filter membership defined by 25C36 adjusted membership. No new variants and no new conditions are allowed.

## Output directory

```text
FX_OUTPUTS/gold_v2_25c42_coreb_g1_right_only_row_level_export_audit_only/
```

Expected outputs:

```text
00_不要_25c42_file_request_list.csv
01_25c42_GOLD_V2_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_AUDIT_ONLY_REPORT.md
02_25c42_coreb_g1_right_only_row_level_export_summary.json
03_25c42_input_audit.csv
04_25c42_variant_full_row_level_compare_rows.csv
05_25c42_variant_right_only_row_level_compare_rows.csv
06_25c42_right_only_by_variant_dataset_policy.csv
07_25c42_right_only_export_reconciliation_matrix.csv
08_25c42_execution_boundary_matrix.csv
09_25c42_acceptance_gate_matrix.csv
10_25c42_next_step_plan.csv
```

## Required row-level columns

Full row-level compare rows and right_only rows must include at least:

```text
variant
dataset
entry_time
policy
_merge
replay_present
target_present
baseline_merge
baseline_replay_present
baseline_target_present
adjusted_replay_present
adjusted_target_present
right_only_reason
source_step
source_artifact
```

`05_25c42_variant_right_only_row_level_compare_rows.csv` must contain only rows where:

```text
_merge == right_only
variant != BASELINE_CURRENT
```

## Reconciliation contract

25C42 must reconcile exported rows to `06_25c41_future_export_reconciliation_contract.csv`.

For every adjusted variant:

```text
exported_both == expected_both
exported_left_only == expected_left_only
exported_right_only == expected_right_only
```

If any count mismatches, 25C42 must return a STOP status and must not recommend driver review.

## Success status

```text
COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_COMPLETED_AUDIT_ONLY_DRIVER_REVIEW_READY
```

## Stop statuses

```text
25C42_STOP_MISSING_INPUT_AUDIT_ONLY
25C42_STOP_HUMAN_ACCEPTANCE_FLAG_MISSING_AUDIT_ONLY
25C42_STOP_25C41_CONTRACT_UNSAFE_AUDIT_ONLY
25C42_STOP_RECONCILIATION_MISMATCH_AUDIT_ONLY
```

## Non-goals / hard stops

```text
No source recovery.
No source mutation.
No rule condition change.
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

## Next-step policy

If reconciliation passes, the next recommended step is:

```text
25C43_COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_AUDIT_ONLY
```

25C43 may review exported right_only rows, but it must still not approve live use, mutate sources, or execute external actions.
