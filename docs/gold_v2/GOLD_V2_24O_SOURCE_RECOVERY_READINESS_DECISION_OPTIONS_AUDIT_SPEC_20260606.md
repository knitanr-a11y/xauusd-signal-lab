# GOLD V2 24O source recovery readiness decision options audit-only spec

Date: 2026-06-06
Step: `24O_SOURCE_RECOVERY_READINESS_DECISION_OPTIONS_AUDIT_ONLY`
Mode: audit-only options

## Purpose

24O reads the successful 24N dry-run review and prepares readiness decision options for a later human decision intake.

24O does not choose a decision.
24O does not run recovery.
24O does not mutate source artifacts.
24O does not finalize source identity.
24O does not enable live, final signal, Discord, MT5, AI API, or live hook.

## Required input folder

`FX_OUTPUTS/gold_v2_24n_source_recovery_dry_run_review_audit_only`

Required 24N files:

- `GOLD_V2_24N_SOURCE_RECOVERY_DRY_RUN_REVIEW_AUDIT_ONLY_REPORT.md`
- `gold_v2_24n_source_recovery_dry_run_review_summary.json`
- `gold_v2_24n_input_audit.csv`
- `gold_v2_24n_dry_run_review.csv`
- `gold_v2_24n_blocked_action_review.csv`
- `gold_v2_24n_noop_integrity_review.csv`
- `gold_v2_24n_integrated_checks.csv`
- `gold_v2_24n_required_next_gates.csv`
- `gold_v2_24n_safety_matrix.csv`

Expected 24N status:

`SOURCE_RECOVERY_DRY_RUN_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Decision options

24O writes options only. Allowed later decision values:

- `KEEP_SOURCE_RECOVERY_BLOCKED_AFTER_DRY_RUN`
- `REQUEST_MORE_DRY_RUN_AUDIT`
- `REJECT_SOURCE_RECOVERY_READINESS`
- `APPROVE_SOURCE_RECOVERY_READINESS_FOR_LATER_INTAKE`

The approve readiness value is not execution. It only means a later intake/routing audit may continue.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24o_source_recovery_readiness_decision_options_audit_only`

Outputs:

- `gold_v2_24o_input_audit.csv`
- `gold_v2_24o_decision_options.csv`
- `gold_v2_24o_human_decision_input_template.json`
- `gold_v2_24o_integrated_checks.csv`
- `gold_v2_24o_required_next_gates.csv`
- `gold_v2_24o_safety_matrix.csv`
- `gold_v2_24o_source_recovery_readiness_decision_options_summary.json`
- `GOLD_V2_24O_SOURCE_RECOVERY_READINESS_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md`

## Success status

`SOURCE_RECOVERY_READINESS_DECISION_OPTIONS_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Stop status

`24O_STOP_SOURCE_RECOVERY_READINESS_DECISION_OPTIONS_INPUTS_OR_SAFETY`

## Next step policy

If 24O passes, the only allowed next audit step is:

`24P_SOURCE_RECOVERY_READINESS_DECISION_INTAKE_AUDIT_ONLY`

24P may only intake a human decision value. It must not run recovery, mutate sources, or enable live/external actions.
