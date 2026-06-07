# GOLD V2 25C45 CoreB G1 incremental damage filter attribution audit spec

Date: 2026-06-08
Step: `25C45_COREB_G1_INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_AUDIT_ONLY`
Mode: audit-only filter attribution

## Purpose

25C45 reads the completed 25C44 route plan, 25C43 incremental-damage rows, and 25C10 baseline filter replay rows, then attributes target-damaging keys back to the baseline replay filter(s) that produced those keys.

This answers the question: which original filters are being removed by the adjusted narrowing variants when baseline target-matching rows become right_only?

25C45 is audit-only. It does not create a new bundle, does not run a dry-run, does not change conditions, and does not approve any variant.

## Source-of-truth context from 25C44

25C44 selected:

```text
selected_route=INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_FIRST
next_recommended_step=25C45_COREB_G1_INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_AUDIT_ONLY
incremental_damage_rows=360
persistent_baseline_right_only_rows=312
```

25C44 also stated that future dry-run remains blocked until attribution, plan, and explicit acceptance.

## Required inputs

Required control inputs:

```text
FX_OUTPUTS/gold_v2_25c44_coreb_g1_right_only_damage_route_plan_audit_only/02_25c44_coreb_g1_right_only_damage_route_plan_summary.json
FX_OUTPUTS/gold_v2_25c44_coreb_g1_right_only_damage_route_plan_audit_only/06_25c44_route_recommendation_matrix.csv
FX_OUTPUTS/gold_v2_25c44_coreb_g1_right_only_damage_route_plan_audit_only/09_25c44_acceptance_gate_matrix.csv
FX_OUTPUTS/gold_v2_25c44_coreb_g1_right_only_damage_route_plan_audit_only/10_25c44_next_step_plan.csv
```

Required evidence inputs:

```text
FX_OUTPUTS/gold_v2_25c43_coreb_g1_right_only_driver_review_audit_only/04_25c43_right_only_driver_classification_matrix.csv
FX_OUTPUTS/gold_v2_25c36_coreb_g1_over_narrowing_adjustment_plan_audit_only/04_25c36_adjusted_bundle_candidate_matrix.csv
FX_OUTPUTS/gold_v2_25c36_coreb_g1_over_narrowing_adjustment_plan_audit_only/05_25c36_adjusted_bundle_membership.csv
FX_OUTPUTS/gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv
```

## Attribution logic

Use only rows from 25C43 where:

```text
driver_class == INCREMENTAL_DAMAGE_FROM_BASELINE_BOTH
```

Join those damaged keys to 25C10 baseline filter replay rows on:

```text
dataset, entry_time, policy
```

Then verify whether the attributed baseline filter is included in the adjusted variant's excluded filter set from 25C36 adjusted membership.

A row is cleanly attributed when:

```text
filter_attributed == true
filter_excluded_by_variant == true
```

If damaged keys cannot be attributed to baseline filters, stop future planning and report the missing attribution.

## Outputs

Output directory:

```text
FX_OUTPUTS/gold_v2_25c45_coreb_g1_incremental_damage_filter_attribution_audit_only/
```

Expected files:

```text
00_不要_25c45_file_request_list.csv
01_25c45_GOLD_V2_COREB_G1_INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_AUDIT_ONLY_REPORT.md
02_25c45_coreb_g1_incremental_damage_filter_attribution_summary.json
03_25c45_input_audit.csv
04_25c45_incremental_damage_key_filter_attribution_rows.csv
05_25c45_filter_damage_by_variant_matrix.csv
06_25c45_variant_excluded_filter_damage_matrix.csv
07_25c45_filter_retention_candidate_matrix.csv
08_25c45_attribution_quality_matrix.csv
09_25c45_execution_boundary_matrix.csv
10_25c45_acceptance_gate_matrix.csv
11_25c45_next_step_plan.csv
```

## Expected status

```text
COREB_G1_INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_COMPLETED_AUDIT_ONLY_RETENTION_PLAN_REQUIRED
```

## Stop statuses

```text
25C45_STOP_MISSING_INPUT_AUDIT_ONLY
25C45_STOP_25C44_CONTRACT_UNSAFE_AUDIT_ONLY
25C45_STOP_ATTRIBUTION_INCOMPLETE_AUDIT_ONLY
```

## Non-goals / hard stops

```text
No source recovery.
No source mutation.
No rule condition change.
No new dry-run.
No new variant search.
No retention bundle execution.
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

## Next-step policy

If attribution completes, the next recommended step should be plan-only:

```text
25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_ONLY
```

25C46 may design a retention-aware recovery plan using attributed filters, but it must not run a dry-run or approve live use.
