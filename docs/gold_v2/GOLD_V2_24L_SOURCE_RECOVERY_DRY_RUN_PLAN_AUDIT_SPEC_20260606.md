# GOLD V2 24L source recovery dry-run plan audit-only spec

Date: 2026-06-06
Step: `24L_SOURCE_RECOVERY_EXECUTION_DRY_RUN_PLAN_AUDIT_ONLY`
Mode: audit-only

## Purpose

24L reads the successful 24K preflight result and writes a dry-run plan for a later no-op dry-run step.

24L does not run recovery.
24L does not modify source artifacts.
24L does not finalize source identity.
24L does not enable live, final signal, Discord, MT5, AI API, or live hook.

## Required input folder

`FX_OUTPUTS/gold_v2_24k_source_recovery_execution_preflight_audit_only`

Required 24K files:

- `GOLD_V2_24K_SOURCE_RECOVERY_EXECUTION_PREFLIGHT_AUDIT_ONLY_REPORT.md`
- `gold_v2_24k_source_recovery_execution_preflight_summary.json`
- `gold_v2_24k_input_audit.csv`
- `gold_v2_24k_preflight_validation.csv`
- `gold_v2_24k_artifact_manifest_review.csv`
- `gold_v2_24k_stop_condition_review.csv`
- `gold_v2_24k_integrated_checks.csv`
- `gold_v2_24k_required_next_gates.csv`
- `gold_v2_24k_safety_matrix.csv`

Expected 24K status:

`SOURCE_RECOVERY_EXECUTION_PREFLIGHT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24l_source_recovery_execution_dry_run_plan_audit_only`

Outputs:

- `gold_v2_24l_input_audit.csv`
- `gold_v2_24l_dry_run_plan.csv`
- `gold_v2_24l_dry_run_input_manifest.csv`
- `gold_v2_24l_expected_noop_outputs.csv`
- `gold_v2_24l_stop_conditions.csv`
- `gold_v2_24l_integrated_checks.csv`
- `gold_v2_24l_required_next_gates.csv`
- `gold_v2_24l_safety_matrix.csv`
- `gold_v2_24l_source_recovery_execution_dry_run_plan_summary.json`
- `GOLD_V2_24L_SOURCE_RECOVERY_EXECUTION_DRY_RUN_PLAN_AUDIT_ONLY_REPORT.md`

## Success status

`SOURCE_RECOVERY_EXECUTION_DRY_RUN_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Stop status

`24L_STOP_SOURCE_RECOVERY_EXECUTION_DRY_RUN_PLAN_INPUTS_OR_SAFETY`

## Next step policy

If 24L passes, the only allowed next audit step is:

`24M_SOURCE_RECOVERY_EXECUTION_DRY_RUN_AUDIT_ONLY`

24M may only run a no-op/dry-run validation. It must not modify source artifacts or enable live/external actions.
