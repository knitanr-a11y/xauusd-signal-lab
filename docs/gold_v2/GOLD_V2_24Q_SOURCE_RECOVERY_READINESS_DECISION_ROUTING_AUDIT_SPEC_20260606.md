# GOLD V2 24Q source recovery readiness decision routing audit-only spec

Date: 2026-06-06
Step: `24Q_SOURCE_RECOVERY_READINESS_DECISION_ROUTING_AUDIT_ONLY`
Mode: audit-only routing

## Purpose

24Q reads the validated 24P readiness decision and routes it to the next audit-only step.

24Q does not choose a decision.
24Q does not run recovery.
24Q does not mutate source artifacts.
24Q does not finalize source identity.
24Q does not enable live, final signal, Discord, MT5, AI API, or live hook.

## Required input folder

`FX_OUTPUTS/gold_v2_24p_source_recovery_readiness_decision_intake_audit_only`

Required 24P files:

- `GOLD_V2_24P_SOURCE_RECOVERY_READINESS_DECISION_INTAKE_AUDIT_ONLY_REPORT.md`
- `gold_v2_24p_source_recovery_readiness_decision_intake_summary.json`
- `gold_v2_24p_human_decision_input.json`
- `gold_v2_24p_human_decision_intake_result.csv`
- `gold_v2_24p_input_audit.csv`
- `gold_v2_24p_integrated_checks.csv`
- `gold_v2_24p_required_next_gates.csv`
- `gold_v2_24p_safety_matrix.csv`

Expected 24P status:

`SOURCE_RECOVERY_READINESS_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Routing table

- `KEEP_SOURCE_RECOVERY_BLOCKED_AFTER_DRY_RUN` -> `24R_SOURCE_RECOVERY_BLOCKED_STATE_RECORD_AUDIT_ONLY`
- `REQUEST_MORE_DRY_RUN_AUDIT` -> `24R_SOURCE_RECOVERY_REQUEST_MORE_DRY_RUN_AUDIT_RESOLUTION_AUDIT_ONLY`
- `REJECT_SOURCE_RECOVERY_READINESS` -> `24R_SOURCE_RECOVERY_READINESS_REJECTION_RECORD_AUDIT_ONLY`
- `APPROVE_SOURCE_RECOVERY_READINESS_FOR_LATER_INTAKE` -> `24R_SOURCE_RECOVERY_READINESS_PLAN_AUDIT_ONLY`

The approve route is readiness planning only. It is not recovery execution.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24q_source_recovery_readiness_decision_routing_audit_only`

Outputs:

- `gold_v2_24q_input_audit.csv`
- `gold_v2_24q_decision_route.csv`
- `gold_v2_24q_integrated_checks.csv`
- `gold_v2_24q_required_next_gates.csv`
- `gold_v2_24q_safety_matrix.csv`
- `gold_v2_24q_source_recovery_readiness_decision_routing_summary.json`
- `GOLD_V2_24Q_SOURCE_RECOVERY_READINESS_DECISION_ROUTING_AUDIT_ONLY_REPORT.md`

## Success status

`SOURCE_RECOVERY_READINESS_DECISION_ROUTED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Stop status

`24Q_STOP_SOURCE_RECOVERY_READINESS_DECISION_ROUTING_INPUTS_OR_SAFETY`

## Next step policy

If the selected route is approve-readiness, the only allowed next audit step is:

`24R_SOURCE_RECOVERY_READINESS_PLAN_AUDIT_ONLY`

24R still must not run recovery, mutate sources, or enable live/external actions.
