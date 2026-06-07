# GOLD V2 24AF source recovery pre-execution final decision routing audit-only spec

Date: 2026-06-07
Step: `24AF_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_ROUTING_AUDIT_ONLY`
Mode: audit-only routing

## Purpose

24AF reads the validated 24AE human-selected value and routes it to the next audit-only branch.

24AF does not choose a value.
24AF does not run recovery.
24AF does not mutate source artifacts.
24AF does not finalize source identity.
24AF does not enable live, final signal, Discord, MT5, AI API, or live hook.

## Required input folder

`FX_OUTPUTS/gold_v2_24ae_source_recovery_pre_execution_final_decision_intake_audit_only`

Required 24AE files:

- `GOLD_V2_24AE_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_INTAKE_AUDIT_ONLY_REPORT.md`
- `gold_v2_24ae_source_recovery_pre_execution_final_decision_intake_summary.json`
- `gold_v2_24ae_human_decision_input.json`
- `gold_v2_24ae_human_decision_input_template.json`
- `gold_v2_24ae_human_decision_intake_result.csv`
- `gold_v2_24ae_input_audit.csv`
- `gold_v2_24ae_integrated_checks.csv`
- `gold_v2_24ae_required_next_gates.csv`
- `gold_v2_24ae_safety_matrix.csv`

Expected 24AE status:

`SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Routing table

- `KEEP_SOURCE_RECOVERY_PRE_EXECUTION_BLOCKED` -> `24AG_SOURCE_RECOVERY_PRE_EXECUTION_BLOCKED_RECORD_AUDIT_ONLY`
- `REQUEST_MORE_SOURCE_RECOVERY_PRE_EXECUTION_REVIEW` -> `24AG_SOURCE_RECOVERY_PRE_EXECUTION_MORE_REVIEW_AUDIT_ONLY`
- `REJECT_SOURCE_RECOVERY_PRE_EXECUTION_READINESS` -> `24AG_SOURCE_RECOVERY_PRE_EXECUTION_REJECTION_RECORD_AUDIT_ONLY`
- `APPROVE_SOURCE_RECOVERY_PRE_EXECUTION_FOR_DRY_RUN_AUDIT_ONLY` -> `24AG_SOURCE_RECOVERY_DRY_RUN_EXECUTION_PLAN_AUDIT_ONLY`

The approve route is dry-run execution planning audit only. It is not source recovery execution.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24af_source_recovery_pre_execution_final_decision_routing_audit_only`

Outputs:

- `gold_v2_24af_input_audit.csv`
- `gold_v2_24af_decision_route.csv`
- `gold_v2_24af_integrated_checks.csv`
- `gold_v2_24af_required_next_gates.csv`
- `gold_v2_24af_safety_matrix.csv`
- `gold_v2_24af_source_recovery_pre_execution_final_decision_routing_summary.json`
- `GOLD_V2_24AF_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_ROUTING_AUDIT_ONLY_REPORT.md`

## Success status

`SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_ROUTED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Stop status

`24AF_STOP_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_ROUTING_INPUTS_OR_SAFETY`

## Next step policy

If routed to the dry-run branch, the only allowed next audit step is:

`24AG_SOURCE_RECOVERY_DRY_RUN_EXECUTION_PLAN_AUDIT_ONLY`

24AG still must not mutate sources, finalize identity, or enable live/external actions.
