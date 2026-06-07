# GOLD V2 25C46 CoreB G1 retention-aware recovery plan audit spec

Date: 2026-06-08
Step: `25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_ONLY`
Mode: audit-only plan

## Purpose

25C46 reads the corrected 25C45 attribution outputs and creates a plan for a later retention-aware contract. It is plan-only and must not execute a replay, change CoreB conditions, approve any variant, or enable live use.

## Count semantics

25C45 corrected the key-count issue:

```text
unique_incremental_damage_keys = 360
filter_attribution_rows = 1260
```

25C46 must use `unique_incremental_damage_keys` as the damaged-key population. Attribution rows are not additive because one damaged key can map to multiple baseline filters.

## Required inputs

From `FX_OUTPUTS/gold_v2_25c45_coreb_g1_incremental_damage_filter_attribution_audit_only/`:

```text
02_25c45_coreb_g1_incremental_damage_filter_attribution_summary.json
04_25c45_incremental_damage_key_filter_attribution_rows.csv
05_25c45_filter_damage_by_variant_matrix.csv
06_25c45_variant_excluded_filter_damage_matrix.csv
07_25c45_filter_retention_candidate_matrix.csv
08_25c45_attribution_quality_matrix.csv
11_25c45_next_step_plan.csv
```

## Plan logic

For each variant and retention-priority cutoff, 25C46 computes unique key coverage:

```text
retained_filters = filters where retention_priority <= cutoff
covered_unique_damage_keys = unique damaged keys with at least one retained filter
uncovered_unique_damage_keys = total_unique_damage_keys - covered_unique_damage_keys
```

The selected future-plan candidate should be the least-damaging representative that covers all known unique damaged keys with the fewest retained filters. Current evidence suggests A002 and A004 are equivalent, so A002 is the representative unless later evidence changes this.

## Outputs

Output directory:

```text
FX_OUTPUTS/gold_v2_25c46_coreb_g1_retention_aware_recovery_plan_audit_only/
```

Expected files:

```text
00_不要_25c46_file_request_list.csv
01_25c46_GOLD_V2_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_ONLY_REPORT.md
02_25c46_coreb_g1_retention_aware_recovery_plan_summary.json
03_25c46_input_audit.csv
04_25c46_retention_candidate_coverage_matrix.csv
05_25c46_selected_recovery_contract_plan.csv
06_25c46_future_dry_run_contract_requirements.csv
07_25c46_risk_and_blocker_matrix.csv
08_25c46_execution_boundary_matrix.csv
09_25c46_acceptance_gate_matrix.csv
10_25c46_next_step_plan.csv
```

## Expected status

```text
COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_READY_AUDIT_ONLY_DRY_RUN_CONTRACT_REQUIRED
```

Next recommended step:

```text
25C47_COREB_G1_RETENTION_AWARE_DRY_RUN_CONTRACT_AUDIT_ONLY
```

25C47 may define the later contract and acceptance gate. It must not execute the later replay.
