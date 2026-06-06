# GOLD V2 24V decision routing audit-only spec

Date: 2026-06-06
Step: `24V_SOURCE_RECOVERY_READINESS_FINAL_DECISION_ROUTING_AUDIT_ONLY`
Mode: audit-only routing

## Purpose

24V reads the validated 24U human-selected value and routes it to the next audit-only branch.

24V does not choose a value.
24V does not run recovery.
24V does not mutate source artifacts.
24V does not finalize source identity.
24V does not enable live, final signal, Discord, MT5, AI API, or live hook.

## Required input folder

`FX_OUTPUTS/gold_v2_24u_source_recovery_readiness_final_decision_intake_audit_only`

Required 24U files:

- `GOLD_V2_24U_SOURCE_RECOVERY_READINESS_FINAL_DECISION_INTAKE_AUDIT_ONLY_REPORT.md`
- `gold_v2_24u_source_recovery_readiness_final_decision_intake_summary.json`
- `gold_v2_24u_human_decision_input.json`
- `gold_v2_24u_human_decision_input_template.json`
- `gold_v2_24u_human_decision_intake_result.csv`
- `gold_v2_24u_input_audit.csv`
- `gold_v2_24u_integrated_checks.csv`
- `gold_v2_24u_required_next_gates.csv`
- `gold_v2_24u_safety_matrix.csv`

Expected 24U status:

`SOURCE_RECOVERY_READINESS_FINAL_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Routing table

- `KEEP_SOURCE_RECOVERY_READINESS_FINAL_BLOCKED` -> `24W_SOURCE_RECOVERY_FINAL_BLOCKED_STATE_RECORD_AUDIT_ONLY`
- `REQUEST_MORE_READINESS_PLAN_REVIEW` -> `24W_SOURCE_RECOVERY_READINESS_MORE_REVIEW_RESOLUTION_AUDIT_ONLY`
- `REJECT_SOURCE_RECOVERY_FINAL_READINESS` -> `24W_SOURCE_RECOVERY_READINESS_FINAL_REJECTION_RECORD_AUDIT_ONLY`
- `APPROVE_SOURCE_RECOVERY_FINAL_READINESS_FOR_EXECUTION_PLANNING_AUDIT_ONLY` -> `24W_SOURCE_RECOVERY_EXECUTION_PLANNING_AUDIT_ONLY`

The approve route is execution-planning audit only. It is not recovery execution.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24v_source_recovery_readiness_final_decision_routing_audit_only`

Outputs:

- `gold_v2_24v_input_audit.csv`
- `gold_v2_24v_decision_route.csv`
- `gold_v2_24v_integrated_checks.csv`
- `gold_v2_24v_required_next_gates.csv`
- `gold_v2_24v_safety_matrix.csv`
- `gold_v2_24v_source_recovery_readiness_final_decision_routing_summary.json`
- `GOLD_V2_24V_SOURCE_RECOVERY_READINESS_FINAL_DECISION_ROUTING_AUDIT_ONLY_REPORT.md`

## Success status

`SOURCE_RECOVERY_READINESS_FINAL_DECISION_ROUTED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Stop status

`24V_STOP_SOURCE_RECOVERY_READINESS_FINAL_DECISION_ROUTING_INPUTS_OR_SAFETY`

## Next step policy

If the selected value routes to planning, the only allowed next audit step is:

`24W_SOURCE_RECOVERY_EXECUTION_PLANNING_AUDIT_ONLY`

24W is planning-only and still must not run recovery, mutate sources, or enable live/external actions.
