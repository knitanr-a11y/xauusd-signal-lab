# GOLD V2 17K MEDIUM full-set dry-run implementation plan audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17K_MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_PLAN_AUDIT_ONLY`
Mode: audit-only

## Purpose

17K writes the implementation plan for a later MEDIUM full-set dry-run artifact.

17K is planning only. It does not implement the dry-run processor, does not execute a dry-run, does not evaluate OHLC, does not create final signals, does not send Discord notifications, does not place MT5 orders, does not call AI API, and does not install a live hook.

## Source of truth

Use only audited 17J outputs and the already audited 17G manifest metadata:

1. `FX_OUTPUTS/gold_v2_17j_medium_full_set_dry_run_design_audit_only/gold_v2_17j_medium_full_set_dry_run_design_summary.json`
2. `FX_OUTPUTS/gold_v2_17j_medium_full_set_dry_run_design_audit_only/gold_v2_17j_design_gate_checks.csv`
3. `FX_OUTPUTS/gold_v2_17j_medium_full_set_dry_run_design_audit_only/gold_v2_17j_dry_run_input_contract.csv`
4. `FX_OUTPUTS/gold_v2_17j_medium_full_set_dry_run_design_audit_only/gold_v2_17j_dry_run_output_contract.csv`
5. `FX_OUTPUTS/gold_v2_17j_medium_full_set_dry_run_design_audit_only/gold_v2_17j_dry_run_stop_conditions.csv`
6. `FX_OUTPUTS/gold_v2_17j_medium_full_set_dry_run_design_audit_only/gold_v2_17j_required_next_gates.csv`
7. `FX_OUTPUTS/gold_v2_17j_medium_full_set_dry_run_design_audit_only/gold_v2_17j_safety_matrix.csv`
8. `FX_OUTPUTS/gold_v2_17g_medium_full_set_candidate_mapping_audit_only/gold_v2_17g_full_set_candidate_manifest.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer executable predicates.

## Expected input state

17J must have status:

`MEDIUM_FULL_SET_DRY_RUN_DESIGN_READY_AUDIT_ONLY_LIVE_BLOCKED`

Expected inherited manifest counts:

- total rows: 309
- `TIER2_HVT`: 1
- `RANGE96_REFINED`: 168
- `VOL_TRMEAN32_REFINED`: 140

17J safety must contain no STOP rows.

17J required next gates must include `17K` as allowed after 17J success.

## Planned future implementation boundary

17K may plan a later script name and output names, but must not create the dry-run implementation itself.

A later step may implement a dry-run processor only if all of the following remain true:

- reads source identity manifest only,
- writes dry-run audit rows only,
- never calls Discord,
- never places MT5 orders,
- never calls AI API,
- never installs a live hook,
- never emits final signal,
- does not notify NO_SIGNAL,
- stops on count/hash/schema mismatches,
- remains audit-only.

## Output folder

`FX_OUTPUTS/gold_v2_17k_medium_full_set_dry_run_implementation_plan_audit_only`

## Main outputs

- `GOLD_V2_17K_MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_PLAN_AUDIT_ONLY_REPORT.md`
- `gold_v2_17k_medium_full_set_dry_run_implementation_plan_summary.json`
- `gold_v2_17k_input_audit.csv`
- `gold_v2_17k_plan_gate_checks.csv`
- `gold_v2_17k_planned_artifacts.csv`
- `gold_v2_17k_planned_processing_steps.csv`
- `gold_v2_17k_planned_stop_conditions.csv`
- `gold_v2_17k_required_next_gates.csv`
- `gold_v2_17k_blockers.csv`
- `gold_v2_17k_safety_matrix.csv`

## Success status

`MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED`

This means only an implementation plan is ready. It does not mean the dry-run implementation exists or can be executed.

## Stop conditions

Stop if:

- any required 17J/17G artifact is missing,
- 17J status is not expected,
- 17J design gate checks or safety contain STOP,
- manifest row counts do not match expectations,
- any planned artifact would enable live/final/external actions,
- any external action flag is true.

## Recommended next step after success

After 17K success, the next possible step is:

`17L_MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY`

17L, if created, must still remain audit-only and must not call external services or emit final signals.
