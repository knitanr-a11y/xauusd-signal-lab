# GOLD V2 24J source recovery plan audit-only spec

Date: 2026-06-06
Step: `24J_SOURCE_RECOVERY_EXECUTION_PLAN_AUDIT_ONLY`
Mode: audit-only

## Purpose

24J reads the successful 24I route and writes a plan/preflight package for a later recovery step.

24J does not run recovery.

24J does not finalize source identity.

24J does not enable live, final signal, Discord, MT5, AI API, or live hook.

## Required input folder

`FX_OUTPUTS/gold_v2_24i_source_recovery_execution_decision_routing_audit_only`

Required 24I files:

- `GOLD_V2_24I_SOURCE_RECOVERY_EXECUTION_DECISION_ROUTING_AUDIT_ONLY_REPORT.md`
- `gold_v2_24i_source_recovery_execution_decision_routing_summary.json`
- `gold_v2_24i_decision_route.csv`
- `gold_v2_24i_input_audit.csv`
- `gold_v2_24i_integrated_checks.csv`
- `gold_v2_24i_required_next_gates.csv`
- `gold_v2_24i_safety_matrix.csv`

Expected 24I route:

- selected value: `APPROVE_SOURCE_RECOVERY_EXECUTION`
- route id: `ROUTE_APPROVE_TO_PLAN_AUDIT_ONLY`
- routed next gate: `24J_SOURCE_RECOVERY_EXECUTION_PLAN_AUDIT_ONLY`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24j_source_recovery_execution_plan_audit_only`

Outputs:

- `gold_v2_24j_input_audit.csv`
- `gold_v2_24j_plan.csv`
- `gold_v2_24j_preflight_checks.csv`
- `gold_v2_24j_stop_conditions.csv`
- `gold_v2_24j_required_artifact_manifest.csv`
- `gold_v2_24j_integrated_checks.csv`
- `gold_v2_24j_required_next_gates.csv`
- `gold_v2_24j_safety_matrix.csv`
- `gold_v2_24j_source_recovery_execution_plan_summary.json`
- `GOLD_V2_24J_SOURCE_RECOVERY_EXECUTION_PLAN_AUDIT_ONLY_REPORT.md`

## Plan content

24J writes a plan only. The plan must record:

- upstream 24I route identity
- source artifacts to be reviewed again before any later action
- preflight checks required before a later recovery attempt
- stop conditions
- forbidden actions that remain blocked

## Success status

`SOURCE_RECOVERY_EXECUTION_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Stop status

`24J_STOP_SOURCE_RECOVERY_EXECUTION_PLAN_INPUTS_OR_SAFETY`

## Next step policy

If 24J passes, the only allowed next audit step is:

`24K_SOURCE_RECOVERY_EXECUTION_PREFLIGHT_AUDIT_ONLY`

24K still must not run recovery. It may only verify that the 24J plan and required artifacts are complete.
