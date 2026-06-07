# GOLD V2 25B8 CoreB condition object dry-run plan audit spec

Date: 2026-06-07
Step: `25B8_COREB_CONDITION_OBJECT_DRY_RUN_PLAN_AUDIT_ONLY`
Mode: audit-only plan, no dry-run execution

## Purpose

25B7 proved that CoreB frozen rules contain non-key condition objects. 25B8 decides whether a non-key-only dry-run can be planned from available source artifacts without approximation.

25B8 does not execute a new replay. It builds a feature/field requirement manifest and checks whether the raw ledger contains the required condition fields.

## Inputs

```text
Files/FX_OUTPUTS/gold_v2_25b7_coreb_frozen_condition_object_semantics_audit_only/gold_v2_25b7_coreb_frozen_condition_object_semantics_summary.json
Files/FX_OUTPUTS/gold_v2_25b7_coreb_frozen_condition_object_semantics_audit_only/gold_v2_25b7_condition_object_inventory.csv
Files/FX_OUTPUTS/gold_v2_25b7_coreb_frozen_condition_object_semantics_audit_only/gold_v2_25b7_key_only_loss_matrix.csv
Files/FX_OUTPUTS/gold_v2_25b7_coreb_frozen_condition_object_semantics_audit_only/gold_v2_25b7_semantics_feasibility_matrix.csv
Files/FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_csv_profile.csv
```

## Output folder

```text
Files/FX_OUTPUTS/gold_v2_25b8_coreb_condition_object_dry_run_plan_audit_only/
```

## Required outputs

```text
GOLD_V2_25B8_COREB_CONDITION_OBJECT_DRY_RUN_PLAN_AUDIT_ONLY_REPORT.md
gold_v2_25b8_input_audit.csv
gold_v2_25b8_required_feature_manifest.csv
gold_v2_25b8_raw_ledger_field_coverage.csv
gold_v2_25b8_condition_object_dry_run_feasibility.csv
gold_v2_25b8_missing_feature_source_requirements.csv
gold_v2_25b8_next_step_plan.csv
gold_v2_25b8_coreb_condition_object_dry_run_plan_summary.json
```

## Planning rules

A later condition-object dry-run is allowed only if the required feature fields are backed by a source-of-truth artifact or a verified feature builder. If the fields are not present in the raw signal ledger, 25B8 must stop before implementation and require source artifact discovery.

## Expected conclusion

The raw signal ledger is expected to lack condition fields such as `donch_pos_96`, `abs_ret_72_atr`, and `ret_96_atr`. In that case, 25B8 should recommend feature-source discovery before any non-key replay implementation.

## Safety

CoreB remains blocked. Source recovery execution, source mutation, final signal, live hook, Discord, MT5, and AI remain off.

Expected status:

```text
COREB_CONDITION_OBJECT_DRY_RUN_PLAN_COMPLETED_AUDIT_ONLY_FEATURE_SOURCE_REQUIRED
```
