# GOLD V2 18I TIER2 row-level source identity extraction dry-run design audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18I_TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_DRY_RUN_DESIGN_AUDIT_ONLY`
Mode: audit-only

## Purpose

18I designs a dry-run extraction workflow using the 18H source identity extraction plan.

18I does not execute extraction. It does not read source data rows. It does not compute row hashes. It does not recover or finalize TIER2 row-level source identity. It does not use OHLC. It does not implement predicates/arbitration, run replay, enable live/final paths, or enable external actions.

## Inputs

Use only 18H outputs:

- `gold_v2_18h_tier2_source_identity_extraction_plan_summary.json`
- `gold_v2_18h_plan_checks.csv`
- `gold_v2_18h_identity_field_mapping_plan.csv`
- `gold_v2_18h_candidate_artifact_ranking.csv`
- `gold_v2_18h_missing_required_fields.csv`
- `gold_v2_18h_required_next_gates.csv`
- `gold_v2_18h_blockers.csv`
- `gold_v2_18h_safety_matrix.csv`

## Output folder

`FX_OUTPUTS/gold_v2_18i_tier2_source_identity_extraction_dry_run_design_audit_only`

## Outputs

- `GOLD_V2_18I_TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_DRY_RUN_DESIGN_AUDIT_ONLY_REPORT.md`
- `gold_v2_18i_tier2_source_identity_extraction_dry_run_design_summary.json`
- `gold_v2_18i_input_audit.csv`
- `gold_v2_18i_design_checks.csv`
- `gold_v2_18i_selected_artifact_design.csv`
- `gold_v2_18i_dry_run_field_recipe.csv`
- `gold_v2_18i_dry_run_stop_conditions.csv`
- `gold_v2_18i_required_next_gates.csv`
- `gold_v2_18i_blockers.csv`
- `gold_v2_18i_safety_matrix.csv`

## Success status

`TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_DRY_RUN_DESIGN_READY_AUDIT_ONLY_SOURCE_RECOVERY_BLOCKED`

## Required next gate

`18J_TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_DRY_RUN_IMPLEMENTATION_PLAN_AUDIT_ONLY`

18J must still be implementation-plan only unless separately authorized. No source recovery execution is allowed after 18I.
