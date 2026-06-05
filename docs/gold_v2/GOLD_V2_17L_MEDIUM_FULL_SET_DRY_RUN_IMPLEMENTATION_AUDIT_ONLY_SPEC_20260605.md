# GOLD V2 17L MEDIUM full-set dry-run implementation audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17L_MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY`
Mode: audit-only

## Purpose

17L implements the first MEDIUM full-set dry-run artifact in audit-only mode.

17L does not evaluate OHLC, does not rediscover candidates, does not compute live predicates, does not create final signals, does not send Discord notifications, does not place MT5 orders, does not call AI API, and does not install a live hook.

The only permitted processing is to load the audited 17G source-identity manifest and write one dry-run audit row per manifest identity.

## Source of truth

Use only audited 17K outputs and the audited 17G manifest:

1. `FX_OUTPUTS/gold_v2_17k_medium_full_set_dry_run_implementation_plan_audit_only/gold_v2_17k_medium_full_set_dry_run_implementation_plan_summary.json`
2. `FX_OUTPUTS/gold_v2_17k_medium_full_set_dry_run_implementation_plan_audit_only/gold_v2_17k_plan_gate_checks.csv`
3. `FX_OUTPUTS/gold_v2_17k_medium_full_set_dry_run_implementation_plan_audit_only/gold_v2_17k_planned_artifacts.csv`
4. `FX_OUTPUTS/gold_v2_17k_medium_full_set_dry_run_implementation_plan_audit_only/gold_v2_17k_planned_processing_steps.csv`
5. `FX_OUTPUTS/gold_v2_17k_medium_full_set_dry_run_implementation_plan_audit_only/gold_v2_17k_planned_stop_conditions.csv`
6. `FX_OUTPUTS/gold_v2_17k_medium_full_set_dry_run_implementation_plan_audit_only/gold_v2_17k_required_next_gates.csv`
7. `FX_OUTPUTS/gold_v2_17k_medium_full_set_dry_run_implementation_plan_audit_only/gold_v2_17k_safety_matrix.csv`
8. `FX_OUTPUTS/gold_v2_17g_medium_full_set_candidate_mapping_audit_only/gold_v2_17g_full_set_candidate_manifest.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer executable predicates.

## Expected input state

17K must have status:

`MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED`

Expected manifest counts:

- total rows: 309
- `TIER2_HVT`: 1
- `RANGE96_REFINED`: 168
- `VOL_TRMEAN32_REFINED`: 140

17K plan/safety must contain no STOP rows.

## Dry-run row policy

Each output dry-run row is an audit record only.

Allowed output fields include:

- manifest identity fields copied from 17G
- component
- source identity type
- source row hash
- dry-run status
- audit-only flags
- prohibited action flags

The dry-run status must be identity-based, such as:

`SOURCE_IDENTITY_OBSERVED_AUDIT_ONLY_NOT_SIGNAL`

Do not write BUY/SELL/NO_SIGNAL as final signals. NO_SIGNAL may not be notified.

## Output folder

`FX_OUTPUTS/gold_v2_17l_medium_full_set_dry_run_implementation_audit_only`

## Main outputs

- `GOLD_V2_17L_MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY_REPORT.md`
- `gold_v2_17l_medium_full_set_dry_run_implementation_summary.json`
- `gold_v2_17l_input_audit.csv`
- `gold_v2_17l_dry_run_candidate_audit.csv`
- `gold_v2_17l_component_counts.csv`
- `gold_v2_17l_implementation_checks.csv`
- `gold_v2_17l_blockers.csv`
- `gold_v2_17l_safety_matrix.csv`

## Success status

`MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_WRITTEN_AUDIT_ONLY_LIVE_BLOCKED`

This means audit-only dry-run rows were written. It does not mean dry-run execution, live execution, final signal, Discord, MT5, AI API, or live hook is allowed.

## Stop conditions

Stop if:

- any required input is missing,
- 17K status is not expected,
- 17K plan/safety contains STOP,
- manifest row counts do not match expectations,
- manifest required columns are missing,
- any output row would set live/final/external action true,
- any code path attempts to use OHLC, Discord, MT5, AI API, or live hook.

## Recommended next step after success

After 17L success, the next possible step is:

`17M_MEDIUM_FULL_SET_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY`

17M must load-smoke 17L outputs only and must remain audit-only.
