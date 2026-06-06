# GOLD V2 24R source recovery readiness plan audit-only spec

Date: 2026-06-06
Step: `24R_SOURCE_RECOVERY_READINESS_PLAN_AUDIT_ONLY`
Mode: audit-only plan

## Purpose

24R reads the successful 24Q readiness route and writes a readiness plan for later review.

24R does not run recovery.
24R does not mutate source artifacts.
24R does not finalize source identity.
24R does not enable live, final signal, Discord, MT5, AI API, or live hook.

## Required input folder

`FX_OUTPUTS/gold_v2_24q_source_recovery_readiness_decision_routing_audit_only`

Required 24Q files:

- `GOLD_V2_24Q_SOURCE_RECOVERY_READINESS_DECISION_ROUTING_AUDIT_ONLY_REPORT.md`
- `gold_v2_24q_source_recovery_readiness_decision_routing_summary.json`
- `gold_v2_24q_input_audit.csv`
- `gold_v2_24q_decision_route.csv`
- `gold_v2_24q_integrated_checks.csv`
- `gold_v2_24q_required_next_gates.csv`
- `gold_v2_24q_safety_matrix.csv`

Expected 24Q status:

`SOURCE_RECOVERY_READINESS_DECISION_ROUTED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

Expected route:

`ROUTE_APPROVE_READINESS_TO_PLAN_AUDIT_ONLY` -> `24R_SOURCE_RECOVERY_READINESS_PLAN_AUDIT_ONLY`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24r_source_recovery_readiness_plan_audit_only`

Outputs:

- `gold_v2_24r_input_audit.csv`
- `gold_v2_24r_readiness_plan.csv`
- `gold_v2_24r_required_evidence_manifest.csv`
- `gold_v2_24r_execution_boundary_matrix.csv`
- `gold_v2_24r_integrated_checks.csv`
- `gold_v2_24r_required_next_gates.csv`
- `gold_v2_24r_safety_matrix.csv`
- `gold_v2_24r_source_recovery_readiness_plan_summary.json`
- `GOLD_V2_24R_SOURCE_RECOVERY_READINESS_PLAN_AUDIT_ONLY_REPORT.md`

## Success status

`SOURCE_RECOVERY_READINESS_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Stop status

`24R_STOP_SOURCE_RECOVERY_READINESS_PLAN_INPUTS_OR_SAFETY`

## Next step policy

If 24R passes, the only allowed next audit step is:

`24S_SOURCE_RECOVERY_READINESS_PLAN_REVIEW_AUDIT_ONLY`

24S reviews the readiness plan only and still must not run recovery, mutate sources, or enable live/external actions.
