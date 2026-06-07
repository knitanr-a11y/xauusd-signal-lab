# GOLD V2 24AE source recovery pre-execution final decision intake audit-only spec

Date: 2026-06-07
Step: `24AE_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_INTAKE_AUDIT_ONLY`
Mode: audit-only intake

## Purpose

24AE reads the successful 24AD decision options and optionally validates one human-selected value.

24AE does not choose a value.
24AE does not run recovery.
24AE does not mutate source artifacts.
24AE does not finalize source identity.
24AE does not enable live, final signal, Discord, MT5, AI API, or live hook.

## Required input folder

`FX_OUTPUTS/gold_v2_24ad_source_recovery_pre_execution_final_decision_options_audit_only`

Required 24AD files:

- `GOLD_V2_24AD_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md`
- `gold_v2_24ad_source_recovery_pre_execution_final_decision_options_summary.json`
- `gold_v2_24ad_input_audit.csv`
- `gold_v2_24ad_decision_options.csv`
- `gold_v2_24ad_human_decision_input_template.json`
- `gold_v2_24ad_integrated_checks.csv`
- `gold_v2_24ad_required_next_gates.csv`
- `gold_v2_24ad_safety_matrix.csv`

Optional 24AE human input:

`FX_OUTPUTS/gold_v2_24ae_source_recovery_pre_execution_final_decision_intake_audit_only/gold_v2_24ae_human_decision_input.json`

## Allowed values

- `KEEP_SOURCE_RECOVERY_PRE_EXECUTION_BLOCKED`
- `REQUEST_MORE_SOURCE_RECOVERY_PRE_EXECUTION_REVIEW`
- `REJECT_SOURCE_RECOVERY_PRE_EXECUTION_READINESS`
- `APPROVE_SOURCE_RECOVERY_PRE_EXECUTION_FOR_DRY_RUN_AUDIT_ONLY`

The approve value is not source recovery execution. It only allows a later dry-run audit branch.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24ae_source_recovery_pre_execution_final_decision_intake_audit_only`

Outputs:

- `gold_v2_24ae_input_audit.csv`
- `gold_v2_24ae_human_decision_input_template.json`
- `gold_v2_24ae_human_decision_intake_result.csv`
- `gold_v2_24ae_integrated_checks.csv`
- `gold_v2_24ae_required_next_gates.csv`
- `gold_v2_24ae_safety_matrix.csv`
- `gold_v2_24ae_source_recovery_pre_execution_final_decision_intake_summary.json`
- `GOLD_V2_24AE_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_INTAKE_AUDIT_ONLY_REPORT.md`

## Status values

If no human input is supplied:

`SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_INTAKE_TEMPLATE_READY_AUDIT_ONLY_DECISION_NOT_SUPPLIED_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

If a valid human input is supplied:

`SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

If input or safety fails:

`24AE_STOP_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_INTAKE_INPUTS_OR_SAFETY`

## Next step policy

If no value is supplied, the only allowed next state is:

`WAIT_FOR_24AE_HUMAN_DECISION_INPUT`

If a valid value is supplied, the only allowed next audit step is:

`24AF_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_ROUTING_AUDIT_ONLY`

24AF still must not run recovery, mutate sources, finalize identity, or enable live/external actions.
