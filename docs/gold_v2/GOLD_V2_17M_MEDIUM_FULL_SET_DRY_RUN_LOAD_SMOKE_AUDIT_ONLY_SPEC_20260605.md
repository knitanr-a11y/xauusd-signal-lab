# GOLD V2 17M MEDIUM full-set dry-run load-smoke audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17M_MEDIUM_FULL_SET_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY`
Mode: audit-only

## Purpose

17M load-smokes the 17L MEDIUM full-set dry-run audit output.

17M validates that the identity-only dry-run audit rows can be loaded and still preserve all audit-only constraints. It does not evaluate OHLC, rediscover candidates, compute executable predicates, generate final signals, send Discord notifications, place MT5 orders, call AI API, or install a live hook.

## Source of truth

Use only 17L audited outputs:

1. `FX_OUTPUTS/gold_v2_17l_medium_full_set_dry_run_implementation_audit_only/gold_v2_17l_medium_full_set_dry_run_implementation_summary.json`
2. `FX_OUTPUTS/gold_v2_17l_medium_full_set_dry_run_implementation_audit_only/gold_v2_17l_dry_run_candidate_audit.csv`
3. `FX_OUTPUTS/gold_v2_17l_medium_full_set_dry_run_implementation_audit_only/gold_v2_17l_component_counts.csv`
4. `FX_OUTPUTS/gold_v2_17l_medium_full_set_dry_run_implementation_audit_only/gold_v2_17l_implementation_checks.csv`
5. `FX_OUTPUTS/gold_v2_17l_medium_full_set_dry_run_implementation_audit_only/gold_v2_17l_safety_matrix.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer executable predicates.

## Expected input state

17L status must be:

`MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_WRITTEN_AUDIT_ONLY_LIVE_BLOCKED`

Expected output rows:

- total dry-run audit rows: 309
- `TIER2_HVT`: 1
- `RANGE96_REFINED`: 168
- `VOL_TRMEAN32_REFINED`: 140

Expected dry-run row status:

`SOURCE_IDENTITY_OBSERVED_AUDIT_ONLY_NOT_SIGNAL`

Expected safety:

- dry-run execution is false
- OHLC evaluated is false
- candidate rediscovered is false
- final signal is false
- Discord is false
- MT5 is false
- AI API is false
- live hook is false
- NO_SIGNAL notification is false

## Output folder

`FX_OUTPUTS/gold_v2_17m_medium_full_set_dry_run_load_smoke_audit_only`

## Main outputs

- `GOLD_V2_17M_MEDIUM_FULL_SET_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`
- `gold_v2_17m_medium_full_set_dry_run_load_smoke_summary.json`
- `gold_v2_17m_input_audit.csv`
- `gold_v2_17m_dry_run_load_checks.csv`
- `gold_v2_17m_component_counts_check.csv`
- `gold_v2_17m_blockers.csv`
- `gold_v2_17m_safety_matrix.csv`

## Success status

`MEDIUM_FULL_SET_DRY_RUN_LOAD_SMOKE_PASSED_AUDIT_ONLY_LIVE_BLOCKED`

This means only that 17L dry-run audit rows were load-smoked. It does not permit live execution or final signals.

## Stop conditions

Stop if:

- any required input is missing,
- 17L status is not expected,
- implementation checks or safety contain STOP,
- row counts do not match,
- required columns are missing,
- dry-run status differs from expected,
- any prohibited flag is true.

## Recommended next step after success

After 17M success, the next possible step is:

`17N_MEDIUM_FULL_SET_DRY_RUN_CONSOLIDATION_AUDIT_ONLY`

17N must remain audit-only and must not enable live/final/external actions.
