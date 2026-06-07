# GOLD V2 24Z source recovery execution final decision intake audit-only spec

Date: 2026-06-07
Step: `24Z_SOURCE_RECOVERY_EXECUTION_FINAL_DECISION_INTAKE_AUDIT_ONLY`
Mode: audit-only intake

## Purpose

24Z reads the successful 24Y decision options and optionally validates one human-selected value.

24Z does not choose a value.
24Z does not run recovery.
24Z does not mutate source artifacts.
24Z does not finalize source identity.
24Z does not enable live, final signal, Discord, MT5, AI API, or live hook.

## Required input folder

`FX_OUTPUTS/gold_v2_24y_source_recovery_execution_final_decision_options_audit_only`

Required 24Y files:

- `GOLD_V2_24Y_SOURCE_RECOVERY_EXECUTION_FINAL_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md`
- `gold_v2_24y_source_recovery_execution_final_decision_options_summary.json`
- `gold_v2_24y_input_audit.csv`
- `gold_v2_24y_decision_options.csv`
- `gold_v2_24y_human_decision_input_template.json`
- `gold_v2_24y_integrated_checks.csv`
- `gold_v2_24y_required_next_gates.csv`
- `gold_v2_24y_safety_matrix.csv`

Optional 24Z human input:

`FX_OUTPUTS/gold_v2_24z_source_recovery_execution_final_decision_intake_audit_only/gold_v2_24z_human_decision_input.json`

## Allowed values

- `KEEP_SOURCE_RECOVERY_EXECUTION_BLOCKED`
- `REQUEST_MORE_SOURCE_RECOVERY_EXECUTION_PLAN_REVIEW`
- `REJECT_SOURCE_RECOVERY_EXECUTION_PLAN`
- `APPROVE_SOURCE_RECOVERY_EXECUTION_PLAN_FOR_PRE_EXECUTION_AUDIT_ONLY`

The approve value is not source recovery execution. It only allows a later pre-execution audit branch.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24z_source_recovery_execution_final_decision_intake_audit_only`

Outputs:

- `gold_v2_24z_input_audit.csv`
- `gold_v2_24z_human_decision_input_template.json`
- `gold_v2_24z_human_decision_intake_result.csv`
- `gold_v2_24z_integrated_checks.csv`
- `gold_v2_24z_required_next_gates.csv`
- `gold_v2_24z_safety_matrix.csv`
- `gold_v2_24z_source_recovery_execution_final_decision_intake_summary.json`
- `GOLD_V2_24Z_SOURCE_RECOVERY_EXECUTION_FINAL_DECISION_INTAKE_AUDIT_ONLY_REPORT.md`

## Status values

If no human input is supplied:

`SOURCE_RECOVERY_EXECUTION_FINAL_DECISION_INTAKE_TEMPLATE_READY_AUDIT_ONLY_DECISION_NOT_SUPPLIED_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

If a valid human input is supplied:

`SOURCE_RECOVERY_EXECUTION_FINAL_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

If input or safety fails:

`24Z_STOP_SOURCE_RECOVERY_EXECUTION_FINAL_DECISION_INTAKE_INPUTS_OR_SAFETY`

## Next step policy

If no value is supplied, the only allowed next state is:

`WAIT_FOR_24Z_HUMAN_DECISION_INPUT`

If a valid value is supplied, the only allowed next audit step is:

`24AA_SOURCE_RECOVERY_EXECUTION_FINAL_DECISION_ROUTING_AUDIT_ONLY`

24AA still must not run recovery, mutate sources, or enable live/external actions.
