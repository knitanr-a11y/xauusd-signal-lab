# GOLD V2 17J MEDIUM full-set dry-run design audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17J_MEDIUM_FULL_SET_DRY_RUN_DESIGN_AUDIT_ONLY`
Mode: audit-only

## Purpose

17J writes the design contract for a later MEDIUM full-set dry-run step.

17J is design only. It does not execute a dry-run, does not evaluate market data, does not create final signals, does not send Discord notifications, does not place MT5 orders, does not call AI API, and does not install a live hook.

## Source of truth

Use only 17I audited outputs and the already loaded 17G manifest metadata:

1. `FX_OUTPUTS/gold_v2_17i_medium_full_set_dry_run_gate_audit_only/gold_v2_17i_medium_full_set_dry_run_gate_summary.json`
2. `FX_OUTPUTS/gold_v2_17i_medium_full_set_dry_run_gate_audit_only/gold_v2_17i_dry_run_gate_checks.csv`
3. `FX_OUTPUTS/gold_v2_17i_medium_full_set_dry_run_gate_audit_only/gold_v2_17i_dry_run_allowed_scope.csv`
4. `FX_OUTPUTS/gold_v2_17i_medium_full_set_dry_run_gate_audit_only/gold_v2_17i_safety_matrix.csv`
5. `FX_OUTPUTS/gold_v2_17g_medium_full_set_candidate_mapping_audit_only/gold_v2_17g_full_set_candidate_manifest.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer executable predicates.

## Expected input state

17I must have status:

`MEDIUM_FULL_SET_DRY_RUN_GATE_READY_AUDIT_ONLY_LIVE_BLOCKED`

Expected allowed scope:

- `17J` is allowed
- `FINAL_SIGNAL` is false
- `DISCORD` is false
- `MT5` is false
- `AI_API` is false
- `LIVE_HOOK` is false

Expected manifest counts inherited from 17G/17H:

- total rows: 309
- `TIER2_HVT`: 1
- `RANGE96_REFINED`: 168
- `VOL_TRMEAN32_REFINED`: 140

## Design outputs

17J writes design-only artifacts for a later dry-run implementation:

- dry-run input contract
- dry-run output contract
- dry-run stop conditions
- dry-run prohibited actions
- required next gate list

The design must explicitly state that a later implementation may only process source-row identities and must not call external services or produce final signals.

## Output folder

`FX_OUTPUTS/gold_v2_17j_medium_full_set_dry_run_design_audit_only`

## Main outputs

- `GOLD_V2_17J_MEDIUM_FULL_SET_DRY_RUN_DESIGN_AUDIT_ONLY_REPORT.md`
- `gold_v2_17j_medium_full_set_dry_run_design_summary.json`
- `gold_v2_17j_input_audit.csv`
- `gold_v2_17j_design_gate_checks.csv`
- `gold_v2_17j_dry_run_input_contract.csv`
- `gold_v2_17j_dry_run_output_contract.csv`
- `gold_v2_17j_dry_run_stop_conditions.csv`
- `gold_v2_17j_required_next_gates.csv`
- `gold_v2_17j_blockers.csv`
- `gold_v2_17j_safety_matrix.csv`

## Success status

`MEDIUM_FULL_SET_DRY_RUN_DESIGN_READY_AUDIT_ONLY_LIVE_BLOCKED`

This means only the design contract is ready. It does not mean dry-run execution, live execution, final signal, or external actions are allowed.

## Stop conditions

Stop if:

- any required input is missing,
- 17I status is not expected,
- 17I gate checks or safety contain STOP,
- allowed scope permits any prohibited external action,
- 17G manifest row counts do not match expected values,
- any external action flag is true.

## Recommended next step after success

After 17J success, the next possible step is:

`17K_MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_PLAN_AUDIT_ONLY`

17K must still be audit-only and must not execute a dry-run or live path unless separately authorized by later gates.
