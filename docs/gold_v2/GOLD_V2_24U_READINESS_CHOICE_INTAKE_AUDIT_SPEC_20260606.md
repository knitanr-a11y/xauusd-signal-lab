# GOLD V2 24U readiness choice intake audit-only spec

Date: 2026-06-06
Step: `24U_SOURCE_RECOVERY_READINESS_FINAL_DECISION_INTAKE_AUDIT_ONLY`
Mode: audit-only intake

## Purpose

24U reads the successful 24T readiness options and optionally validates one human-selected value.

24U does not choose a value.
24U does not run recovery.
24U does not mutate source artifacts.
24U does not finalize source identity.
24U does not enable live, final signal, Discord, MT5, AI API, or live hook.

## Required input folder

`FX_OUTPUTS/gold_v2_24t_source_recovery_readiness_final_decision_options_audit_only`

Required 24T files:

- `GOLD_V2_24T_SOURCE_RECOVERY_READINESS_FINAL_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md`
- `gold_v2_24t_source_recovery_readiness_final_decision_options_summary.json`
- `gold_v2_24t_input_audit.csv`
- `gold_v2_24t_decision_options.csv`
- `gold_v2_24t_human_decision_input_template.json`
- `gold_v2_24t_integrated_checks.csv`
- `gold_v2_24t_required_next_gates.csv`
- `gold_v2_24t_safety_matrix.csv`

Optional 24U human input:

`FX_OUTPUTS/gold_v2_24u_source_recovery_readiness_final_decision_intake_audit_only/gold_v2_24u_human_decision_input.json`

## Allowed values

- `KEEP_SOURCE_RECOVERY_READINESS_FINAL_BLOCKED`
- `REQUEST_MORE_READINESS_PLAN_REVIEW`
- `REJECT_SOURCE_RECOVERY_FINAL_READINESS`
- `APPROVE_SOURCE_RECOVERY_FINAL_READINESS_FOR_EXECUTION_PLANNING_AUDIT_ONLY`

The approve value is still not recovery execution. It only allows a later routing audit to continue.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24u_source_recovery_readiness_final_decision_intake_audit_only`

Outputs:

- `gold_v2_24u_input_audit.csv`
- `gold_v2_24u_human_decision_input_template.json`
- `gold_v2_24u_human_decision_intake_result.csv`
- `gold_v2_24u_integrated_checks.csv`
- `gold_v2_24u_required_next_gates.csv`
- `gold_v2_24u_safety_matrix.csv`
- `gold_v2_24u_source_recovery_readiness_final_decision_intake_summary.json`
- `GOLD_V2_24U_SOURCE_RECOVERY_READINESS_FINAL_DECISION_INTAKE_AUDIT_ONLY_REPORT.md`

## Status values

If no human input is supplied:

`SOURCE_RECOVERY_READINESS_FINAL_DECISION_INTAKE_TEMPLATE_READY_AUDIT_ONLY_DECISION_NOT_SUPPLIED_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

If a valid human input is supplied:

`SOURCE_RECOVERY_READINESS_FINAL_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

If input or safety fails:

`24U_STOP_SOURCE_RECOVERY_READINESS_FINAL_DECISION_INTAKE_INPUTS_OR_SAFETY`

## Next step policy

If no value is supplied, the only allowed next state is:

`WAIT_FOR_24U_HUMAN_DECISION_INPUT`

If a valid value is supplied, the only allowed next audit step is:

`24V_SOURCE_RECOVERY_READINESS_FINAL_DECISION_ROUTING_AUDIT_ONLY`

24V still must not run recovery, mutate sources, or enable live/external actions.
