# GOLD V2 24T source recovery readiness final decision options audit-only spec

Date: 2026-06-06
Step: `24T_SOURCE_RECOVERY_READINESS_FINAL_DECISION_OPTIONS_AUDIT_ONLY`
Mode: audit-only options

## Purpose

24T reads the successful 24S readiness plan review and prepares final readiness decision options for a later human decision intake.

24T does not choose a decision.
24T does not run recovery.
24T does not mutate source artifacts.
24T does not finalize source identity.
24T does not enable live, final signal, Discord, MT5, AI API, or live hook.

## Required input folder

`FX_OUTPUTS/gold_v2_24s_source_recovery_readiness_plan_review_audit_only`

Required 24S files:

- `GOLD_V2_24S_SOURCE_RECOVERY_READINESS_PLAN_REVIEW_AUDIT_ONLY_REPORT.md`
- `gold_v2_24s_source_recovery_readiness_plan_review_summary.json`
- `gold_v2_24s_input_audit.csv`
- `gold_v2_24s_plan_review.csv`
- `gold_v2_24s_evidence_manifest_review.csv`
- `gold_v2_24s_execution_boundary_review.csv`
- `gold_v2_24s_integrated_checks.csv`
- `gold_v2_24s_required_next_gates.csv`
- `gold_v2_24s_safety_matrix.csv`

Expected 24S status:

`SOURCE_RECOVERY_READINESS_PLAN_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Decision options

24T writes options only. Allowed later decision values:

- `KEEP_SOURCE_RECOVERY_READINESS_FINAL_BLOCKED`
- `REQUEST_MORE_READINESS_PLAN_REVIEW`
- `REJECT_SOURCE_RECOVERY_FINAL_READINESS`
- `APPROVE_SOURCE_RECOVERY_FINAL_READINESS_FOR_EXECUTION_PLANNING_AUDIT_ONLY`

The approve final readiness value is not source recovery execution. It only permits a later execution-planning audit branch.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24t_source_recovery_readiness_final_decision_options_audit_only`

Outputs:

- `gold_v2_24t_input_audit.csv`
- `gold_v2_24t_decision_options.csv`
- `gold_v2_24t_human_decision_input_template.json`
- `gold_v2_24t_integrated_checks.csv`
- `gold_v2_24t_required_next_gates.csv`
- `gold_v2_24t_safety_matrix.csv`
- `gold_v2_24t_source_recovery_readiness_final_decision_options_summary.json`
- `GOLD_V2_24T_SOURCE_RECOVERY_READINESS_FINAL_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md`

## Success status

`SOURCE_RECOVERY_READINESS_FINAL_DECISION_OPTIONS_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Stop status

`24T_STOP_SOURCE_RECOVERY_READINESS_FINAL_DECISION_OPTIONS_INPUTS_OR_SAFETY`

## Next step policy

If 24T passes, the only allowed next audit step is:

`24U_SOURCE_RECOVERY_READINESS_FINAL_DECISION_INTAKE_AUDIT_ONLY`

24U may only intake a human decision value. It must not run recovery, mutate sources, or enable live/external actions.
