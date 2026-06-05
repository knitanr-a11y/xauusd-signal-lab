# GOLD V2 17I MEDIUM full-set dry-run gate audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17I_MEDIUM_FULL_SET_DRY_RUN_GATE_AUDIT_ONLY`
Mode: audit-only

## Purpose

17I verifies whether the MEDIUM full-set manifest has passed enough audit gates to allow a later dry-run design step.

17I does not run a live evaluator, does not create final signals, does not send Discord messages, does not place MT5 orders, does not call AI API, and does not install a live hook.

## Source of truth

Use only 17H audited outputs:

1. `FX_OUTPUTS/gold_v2_17h_medium_full_set_load_smoke_audit_only/gold_v2_17h_medium_full_set_load_smoke_summary.json`
2. `FX_OUTPUTS/gold_v2_17h_medium_full_set_load_smoke_audit_only/gold_v2_17h_manifest_load_checks.csv`
3. `FX_OUTPUTS/gold_v2_17h_medium_full_set_load_smoke_audit_only/gold_v2_17h_component_counts_check.csv`
4. `FX_OUTPUTS/gold_v2_17h_medium_full_set_load_smoke_audit_only/gold_v2_17h_safety_matrix.csv`
5. `FX_OUTPUTS/gold_v2_17h_medium_full_set_load_smoke_audit_only/gold_v2_17h_blockers.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer executable predicates.

## Expected input state

17H status must be:

`MEDIUM_FULL_SET_LOAD_SMOKE_PASSED_AUDIT_ONLY_LIVE_BLOCKED`

Expected load-smoke state:

- manifest load-smoke passed
- manifest rows = 309
- TIER2_HVT = 1
- RANGE96_REFINED = 168
- VOL_TRMEAN32_REFINED = 140
- no manifest load check STOP rows
- no safety STOP rows

## Dry-run gate meaning

17I may mark a later dry-run design step as allowed only in audit-only mode.

The output must keep:

- `medium_live_evaluator_allowed = false`
- `final_signal_allowed = false`
- `discord_send_allowed = false`
- `mt5_order_allowed = false`
- `ai_api_allowed = false`
- `live_hook_allowed = false`

## Output folder

`FX_OUTPUTS/gold_v2_17i_medium_full_set_dry_run_gate_audit_only`

## Main outputs

- `GOLD_V2_17I_MEDIUM_FULL_SET_DRY_RUN_GATE_AUDIT_ONLY_REPORT.md`
- `gold_v2_17i_medium_full_set_dry_run_gate_summary.json`
- `gold_v2_17i_input_audit.csv`
- `gold_v2_17i_dry_run_gate_checks.csv`
- `gold_v2_17i_dry_run_allowed_scope.csv`
- `gold_v2_17i_blockers.csv`
- `gold_v2_17i_safety_matrix.csv`

## Success status

`MEDIUM_FULL_SET_DRY_RUN_GATE_READY_AUDIT_ONLY_LIVE_BLOCKED`

This means only a later dry-run design step is allowed. It does not mean trading/live/final signal is allowed.

## Stop conditions

Stop if:

- any required 17H artifact is missing,
- 17H status is not expected,
- manifest load-smoke is not passed,
- manifest counts do not match,
- load checks or safety contain STOP,
- any external action flag is true.

## Recommended next step after success

After 17I success, the next step may be `17J_MEDIUM_FULL_SET_DRY_RUN_DESIGN_AUDIT_ONLY`.

17J must still be dry-run design only and must not execute final signals or external actions.
