# GOLD V2 24AA source recovery execution final decision routing audit-only spec

Date: 2026-06-07
Step: `24AA_SOURCE_RECOVERY_EXECUTION_FINAL_DECISION_ROUTING_AUDIT_ONLY`
Mode: audit-only routing

## Purpose

24AA reads the validated 24Z human-selected value and routes it to the next audit-only branch.

24AA does not choose a value.
24AA does not run recovery.
24AA does not mutate source artifacts.
24AA does not finalize source identity.
24AA does not enable live, final signal, Discord, MT5, AI API, or live hook.

## Required input folder

`FX_OUTPUTS/gold_v2_24z_source_recovery_execution_final_decision_intake_audit_only`

Required 24Z files:

- `GOLD_V2_24Z_SOURCE_RECOVERY_EXECUTION_FINAL_DECISION_INTAKE_AUDIT_ONLY_REPORT.md`
- `gold_v2_24z_source_recovery_execution_final_decision_intake_summary.json`
- `gold_v2_24z_human_decision_input.json`
- `gold_v2_24z_human_decision_input_template.json`
- `gold_v2_24z_human_decision_intake_result.csv`
- `gold_v2_24z_input_audit.csv`
- `gold_v2_24z_integrated_checks.csv`
- `gold_v2_24z_required_next_gates.csv`
- `gold_v2_24z_safety_matrix.csv`

Expected 24Z status:

`SOURCE_RECOVERY_EXECUTION_FINAL_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Routing table

- `KEEP_SOURCE_RECOVERY_EXECUTION_BLOCKED` -> `24AB_SOURCE_RECOVERY_EXECUTION_BLOCKED_RECORD_AUDIT_ONLY`
- `REQUEST_MORE_SOURCE_RECOVERY_EXECUTION_PLAN_REVIEW` -> `24AB_SOURCE_RECOVERY_EXECUTION_PLAN_MORE_REVIEW_AUDIT_ONLY`
- `REJECT_SOURCE_RECOVERY_EXECUTION_PLAN` -> `24AB_SOURCE_RECOVERY_EXECUTION_PLAN_REJECTION_RECORD_AUDIT_ONLY`
- `APPROVE_SOURCE_RECOVERY_EXECUTION_PLAN_FOR_PRE_EXECUTION_AUDIT_ONLY` -> `24AB_SOURCE_RECOVERY_PRE_EXECUTION_READINESS_PLAN_AUDIT_ONLY`

The approve route is pre-execution readiness planning audit only. It is not source recovery execution.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24aa_source_recovery_execution_final_decision_routing_audit_only`

Outputs:

- `gold_v2_24aa_input_audit.csv`
- `gold_v2_24aa_decision_route.csv`
- `gold_v2_24aa_integrated_checks.csv`
- `gold_v2_24aa_required_next_gates.csv`
- `gold_v2_24aa_safety_matrix.csv`
- `gold_v2_24aa_source_recovery_execution_final_decision_routing_summary.json`
- `GOLD_V2_24AA_SOURCE_RECOVERY_EXECUTION_FINAL_DECISION_ROUTING_AUDIT_ONLY_REPORT.md`

## Success status

`SOURCE_RECOVERY_EXECUTION_FINAL_DECISION_ROUTED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Stop status

`24AA_STOP_SOURCE_RECOVERY_EXECUTION_FINAL_DECISION_ROUTING_INPUTS_OR_SAFETY`

## Next step policy

If routed to the approve branch, the only allowed next audit step is:

`24AB_SOURCE_RECOVERY_PRE_EXECUTION_READINESS_PLAN_AUDIT_ONLY`

24AB still must not run recovery, mutate sources, finalize identity, or enable live/external actions.
