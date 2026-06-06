# GOLD V2 24P source recovery readiness decision intake audit-only spec

Date: 2026-06-06
Step: `24P_SOURCE_RECOVERY_READINESS_DECISION_INTAKE_AUDIT_ONLY`
Mode: audit-only human decision intake

## Purpose

24P reads the successful 24O readiness decision options and optionally validates one human-selected decision value.

24P does not choose a decision.
24P does not run recovery.
24P does not mutate source artifacts.
24P does not finalize source identity.
24P does not enable live, final signal, Discord, MT5, AI API, or live hook.

## Required input folder

`FX_OUTPUTS/gold_v2_24o_source_recovery_readiness_decision_options_audit_only`

Required 24O files:

- `GOLD_V2_24O_SOURCE_RECOVERY_READINESS_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md`
- `gold_v2_24o_source_recovery_readiness_decision_options_summary.json`
- `gold_v2_24o_input_audit.csv`
- `gold_v2_24o_decision_options.csv`
- `gold_v2_24o_human_decision_input_template.json`
- `gold_v2_24o_integrated_checks.csv`
- `gold_v2_24o_required_next_gates.csv`
- `gold_v2_24o_safety_matrix.csv`

Optional 24P human input:

`FX_OUTPUTS/gold_v2_24p_source_recovery_readiness_decision_intake_audit_only/gold_v2_24p_human_decision_input.json`

## Allowed decision values

- `KEEP_SOURCE_RECOVERY_BLOCKED_AFTER_DRY_RUN`
- `REQUEST_MORE_DRY_RUN_AUDIT`
- `REJECT_SOURCE_RECOVERY_READINESS`
- `APPROVE_SOURCE_RECOVERY_READINESS_FOR_LATER_INTAKE`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24p_source_recovery_readiness_decision_intake_audit_only`

Outputs:

- `gold_v2_24p_input_audit.csv`
- `gold_v2_24p_human_decision_input_template.json`
- `gold_v2_24p_human_decision_intake_result.csv`
- `gold_v2_24p_integrated_checks.csv`
- `gold_v2_24p_required_next_gates.csv`
- `gold_v2_24p_safety_matrix.csv`
- `gold_v2_24p_source_recovery_readiness_decision_intake_summary.json`
- `GOLD_V2_24P_SOURCE_RECOVERY_READINESS_DECISION_INTAKE_AUDIT_ONLY_REPORT.md`

## Status values

If no human input is supplied:

`SOURCE_RECOVERY_READINESS_DECISION_INTAKE_TEMPLATE_READY_AUDIT_ONLY_DECISION_NOT_SUPPLIED_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

If a valid human input is supplied:

`SOURCE_RECOVERY_READINESS_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

If input/safety fails:

`24P_STOP_SOURCE_RECOVERY_READINESS_DECISION_INTAKE_INPUTS_OR_SAFETY`

## Next step policy

If no decision is supplied, the only allowed next state is:

`WAIT_FOR_24P_HUMAN_DECISION_INPUT`

If a valid decision is supplied, the only allowed next audit step is:

`24Q_SOURCE_RECOVERY_READINESS_DECISION_ROUTING_AUDIT_ONLY`

24Q still must not run recovery, mutate sources, or enable live/external actions.
