# GOLD V2 25C44 CoreB G1 right_only damage route plan audit spec

Date: 2026-06-08
Step: `25C44_COREB_G1_RIGHT_ONLY_DAMAGE_ROUTE_PLAN_AUDIT_ONLY`
Mode: audit-only route plan

## Purpose

25C44 reads the completed 25C43 right_only driver review and selects the next safe non-live route.

25C43 proved that the adjusted narrowing variants create incremental damage from baseline-matching rows. 25C44 must not run a dry-run or propose adoption. It only decides what evidence is still missing before any retention-aware recovery can be designed.

## Source-of-truth context from 25C43

25C43 completed with:

```text
status=COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_COMPLETED_AUDIT_ONLY_NEXT_PLAN_REQUIRED
right_only_row_count=672
incremental_damage_row_count=360
persistent_baseline_right_only_row_count=312
A002/A004 right_only sets identical=true
next_recommended_step=25C44_COREB_G1_RIGHT_ONLY_DAMAGE_ROUTE_PLAN_AUDIT_ONLY
```

Important interpretation:

```text
baseline_merge=both rows are true incremental damage from adjusted narrowing.
baseline_merge=right_only rows were already target-only before adjusted narrowing.
```

25C43 classified incremental damage by variant:

```text
A001 incremental_damage_rows=100
A002 incremental_damage_rows=69
A003 incremental_damage_rows=122
A004 incremental_damage_rows=69
```

This means A002/A004 are the least damaging tested variants, but they are still not safe, not approved, and not live-ready.

## Required inputs

All inputs are read from:

```text
FX_OUTPUTS/gold_v2_25c43_coreb_g1_right_only_driver_review_audit_only/
```

Required files:

```text
02_25c43_coreb_g1_right_only_driver_review_summary.json
05_25c43_incremental_damage_by_variant_dataset_policy.csv
06_25c43_right_only_variant_overlap_matrix.csv
08_25c43_driver_review_findings_matrix.csv
09_25c43_execution_boundary_matrix.csv
10_25c43_acceptance_gate_matrix.csv
11_25c43_next_step_plan.csv
```

## Route logic

25C44 should recommend filter attribution before any retention-aware recovery plan because 25C43 identifies damaged keys but not the original baseline replay filter(s) that produced those keys.

Recommended route:

```text
25C45_COREB_G1_INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_AUDIT_ONLY
```

25C45 should read 25C43 incremental-damage keys and existing 25C10 filter replay rows to attribute damaged target-matching keys back to baseline replay filters. It should still be audit-only and no dry-run.

## Non-goals / hard stops

```text
No source recovery.
No source mutation.
No rule condition change.
No new dry-run.
No new variant search.
No A002/A004 adoption.
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

## Outputs

Output directory:

```text
FX_OUTPUTS/gold_v2_25c44_coreb_g1_right_only_damage_route_plan_audit_only/
```

Expected files:

```text
00_不要_25c44_file_request_list.csv
01_25c44_GOLD_V2_COREB_G1_RIGHT_ONLY_DAMAGE_ROUTE_PLAN_AUDIT_ONLY_REPORT.md
02_25c44_coreb_g1_right_only_damage_route_plan_summary.json
03_25c44_input_audit.csv
04_25c44_route_evidence_matrix.csv
05_25c44_route_option_matrix.csv
06_25c44_route_recommendation_matrix.csv
07_25c44_dry_run_blocker_matrix.csv
08_25c44_execution_boundary_matrix.csv
09_25c44_acceptance_gate_matrix.csv
10_25c44_next_step_plan.csv
```

## Expected status

```text
COREB_G1_RIGHT_ONLY_DAMAGE_ROUTE_PLAN_READY_AUDIT_ONLY_FILTER_ATTRIBUTION_REQUIRED
```

## Stop statuses

```text
25C44_STOP_MISSING_INPUT_AUDIT_ONLY
25C44_STOP_25C43_CONTRACT_UNSAFE_AUDIT_ONLY
```

## Next-step policy

If 25C44 completes, the next recommended step is:

```text
25C45_COREB_G1_INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_AUDIT_ONLY
```

25C45 may attribute damaged keys to original filters, but it must still not run a dry-run, mutate source, approve variants, or perform external/live actions.
