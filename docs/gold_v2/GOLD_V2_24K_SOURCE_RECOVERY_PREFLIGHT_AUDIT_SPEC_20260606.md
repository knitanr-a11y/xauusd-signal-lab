# GOLD V2 24K source recovery preflight audit-only spec

Date: 2026-06-06
Step: `24K_SOURCE_RECOVERY_EXECUTION_PREFLIGHT_AUDIT_ONLY`
Mode: audit-only

## Purpose

24K reads the successful 24J plan package and verifies that the plan, preflight checks, stop conditions, and artifact manifest are complete.

24K does not run recovery.

24K does not finalize source identity.

24K does not enable live, final signal, Discord, MT5, AI API, or live hook.

## Required input folder

`FX_OUTPUTS/gold_v2_24j_source_recovery_execution_plan_audit_only`

Required 24J files:

- `GOLD_V2_24J_SOURCE_RECOVERY_EXECUTION_PLAN_AUDIT_ONLY_REPORT.md`
- `gold_v2_24j_source_recovery_execution_plan_summary.json`
- `gold_v2_24j_input_audit.csv`
- `gold_v2_24j_plan.csv`
- `gold_v2_24j_preflight_checks.csv`
- `gold_v2_24j_stop_conditions.csv`
- `gold_v2_24j_required_artifact_manifest.csv`
- `gold_v2_24j_integrated_checks.csv`
- `gold_v2_24j_required_next_gates.csv`
- `gold_v2_24j_safety_matrix.csv`

Expected 24J status:

`SOURCE_RECOVERY_EXECUTION_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24k_source_recovery_execution_preflight_audit_only`

Outputs:

- `gold_v2_24k_input_audit.csv`
- `gold_v2_24k_preflight_validation.csv`
- `gold_v2_24k_artifact_manifest_review.csv`
- `gold_v2_24k_stop_condition_review.csv`
- `gold_v2_24k_integrated_checks.csv`
- `gold_v2_24k_required_next_gates.csv`
- `gold_v2_24k_safety_matrix.csv`
- `gold_v2_24k_source_recovery_execution_preflight_summary.json`
- `GOLD_V2_24K_SOURCE_RECOVERY_EXECUTION_PREFLIGHT_AUDIT_ONLY_REPORT.md`

## Success status

`SOURCE_RECOVERY_EXECUTION_PREFLIGHT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Stop status

`24K_STOP_SOURCE_RECOVERY_EXECUTION_PREFLIGHT_INPUTS_OR_SAFETY`

## Next step policy

If 24K passes, the only allowed next audit step is:

`24L_SOURCE_RECOVERY_EXECUTION_DRY_RUN_PLAN_AUDIT_ONLY`

24L still must not enable live or external actions.
