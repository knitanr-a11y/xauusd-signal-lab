# GOLD V2 18J TIER2 source identity dry-run implementation plan audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18J_TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_PLAN_AUDIT_ONLY`
Mode: audit-only

## Purpose

18J converts the corrected 18I dry-run design into an implementation plan only.

18J does not implement or run the dry-run. It does not read source data rows. It does not compute row hashes. It does not recover or finalize TIER2 row-level source identity. It does not use OHLC. It does not implement predicates/arbitration, run replay, enable live/final paths, or enable external actions.

## Inputs

Use only 18I outputs:

- `gold_v2_18i_tier2_source_identity_extraction_dry_run_design_summary.json`
- `gold_v2_18i_design_checks.csv`
- `gold_v2_18i_selected_artifact_design.csv`
- `gold_v2_18i_dry_run_field_recipe.csv`
- `gold_v2_18i_dry_run_stop_conditions.csv`
- `gold_v2_18i_required_next_gates.csv`
- `gold_v2_18i_blockers.csv`
- `gold_v2_18i_safety_matrix.csv`

## Output folder

`FX_OUTPUTS/gold_v2_18j_tier2_source_identity_dry_run_implementation_plan_audit_only`

## Outputs

- `GOLD_V2_18J_TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_PLAN_AUDIT_ONLY_REPORT.md`
- `gold_v2_18j_tier2_source_identity_dry_run_implementation_plan_summary.json`
- `gold_v2_18j_input_audit.csv`
- `gold_v2_18j_plan_checks.csv`
- `gold_v2_18j_planned_artifacts.csv`
- `gold_v2_18j_planned_processing_steps.csv`
- `gold_v2_18j_planned_output_contract.csv`
- `gold_v2_18j_planned_stop_conditions.csv`
- `gold_v2_18j_required_next_gates.csv`
- `gold_v2_18j_blockers.csv`
- `gold_v2_18j_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_PLAN_READY_AUDIT_ONLY_DRY_RUN_EXECUTION_BLOCKED`

## Required next gate

`18K_TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY`

18K must not be created unless the plan is reviewed. 18K may still only implement an audit-only dry-run, not source recovery execution or live/final behavior.
