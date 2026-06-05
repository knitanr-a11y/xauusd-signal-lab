# GOLD V2 17N MEDIUM full-set dry-run consolidation audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17N_MEDIUM_FULL_SET_DRY_RUN_CONSOLIDATION_AUDIT_ONLY`
Mode: audit-only

## Purpose

17N consolidates the completed MEDIUM full-set dry-run audit chain through 17M.

17N is a status consolidation and gap-definition step only. It does not evaluate OHLC, rediscover candidates, compute executable predicates, generate final signals, send Discord notifications, place MT5 orders, call AI API, or install a live hook.

## Source of truth

Use only 17M audited outputs:

1. `FX_OUTPUTS/gold_v2_17m_medium_full_set_dry_run_load_smoke_audit_only/gold_v2_17m_medium_full_set_dry_run_load_smoke_summary.json`
2. `FX_OUTPUTS/gold_v2_17m_medium_full_set_dry_run_load_smoke_audit_only/gold_v2_17m_dry_run_load_checks.csv`
3. `FX_OUTPUTS/gold_v2_17m_medium_full_set_dry_run_load_smoke_audit_only/gold_v2_17m_component_counts_check.csv`
4. `FX_OUTPUTS/gold_v2_17m_medium_full_set_dry_run_load_smoke_audit_only/gold_v2_17m_safety_matrix.csv`
5. `FX_OUTPUTS/gold_v2_17m_medium_full_set_dry_run_load_smoke_audit_only/gold_v2_17m_blockers.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer executable predicates.

## Expected input state

17M must have status:

`MEDIUM_FULL_SET_DRY_RUN_LOAD_SMOKE_PASSED_AUDIT_ONLY_LIVE_BLOCKED`

Expected counts:

- total loaded dry-run rows: 309
- `TIER2_HVT`: 1
- `RANGE96_REFINED`: 168
- `VOL_TRMEAN32_REFINED`: 140

Expected safety:

- dry-run execution false
- medium live evaluator false
- final signal false
- Discord false
- MT5 false
- AI API false
- live hook false
- NO_SIGNAL notification false

## Output folder

`FX_OUTPUTS/gold_v2_17n_medium_full_set_dry_run_consolidation_audit_only`

## Main outputs

- `GOLD_V2_17N_MEDIUM_FULL_SET_DRY_RUN_CONSOLIDATION_AUDIT_ONLY_REPORT.md`
- `gold_v2_17n_medium_full_set_dry_run_consolidation_summary.json`
- `gold_v2_17n_input_audit.csv`
- `gold_v2_17n_consolidation_checks.csv`
- `gold_v2_17n_consolidation_matrix.csv`
- `gold_v2_17n_required_next_gates.csv`
- `gold_v2_17n_blockers.csv`
- `gold_v2_17n_safety_matrix.csv`

## Success status

`MEDIUM_FULL_SET_DRY_RUN_CONSOLIDATED_AUDIT_ONLY_LIVE_BLOCKED`

This means the dry-run audit chain has been consolidated. It does not allow live execution or final signals.

## Stop conditions

Stop if:

- any required input is missing,
- 17M status is not expected,
- 17M load checks or safety contain STOP,
- row counts differ from expectations,
- any external action flag is true.

## Recommended next step after success

After 17N success, the next possible step is:

`17O_MEDIUM_FULL_SET_EXECUTABLE_PARITY_GAP_ANALYSIS_AUDIT_ONLY`

17O must remain audit-only. It may define what is still missing for executable/live parity, but it must not implement live execution or final signals.
