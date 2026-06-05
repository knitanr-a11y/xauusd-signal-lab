# GOLD V2 17O MEDIUM full-set executable parity gap analysis audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17O_MEDIUM_FULL_SET_EXECUTABLE_PARITY_GAP_ANALYSIS_AUDIT_ONLY`
Mode: audit-only

## Purpose

17O analyzes the remaining gap between the completed identity-only dry-run audit chain and any future executable/live parity path.

17O is gap analysis only. It does not implement executable predicates, does not evaluate OHLC, does not rediscover candidates, does not create final signals, does not send Discord notifications, does not place MT5 orders, does not call AI API, and does not install a live hook.

## Source of truth

Use only 17N audited outputs and, for gap sizing, the 17G manifest:

1. `FX_OUTPUTS/gold_v2_17n_medium_full_set_dry_run_consolidation_audit_only/gold_v2_17n_medium_full_set_dry_run_consolidation_summary.json`
2. `FX_OUTPUTS/gold_v2_17n_medium_full_set_dry_run_consolidation_audit_only/gold_v2_17n_consolidation_checks.csv`
3. `FX_OUTPUTS/gold_v2_17n_medium_full_set_dry_run_consolidation_audit_only/gold_v2_17n_consolidation_matrix.csv`
4. `FX_OUTPUTS/gold_v2_17n_medium_full_set_dry_run_consolidation_audit_only/gold_v2_17n_required_next_gates.csv`
5. `FX_OUTPUTS/gold_v2_17n_medium_full_set_dry_run_consolidation_audit_only/gold_v2_17n_safety_matrix.csv`
6. `FX_OUTPUTS/gold_v2_17g_medium_full_set_candidate_mapping_audit_only/gold_v2_17g_full_set_candidate_manifest.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer executable predicates.

## Expected input state

17N status must be:

`MEDIUM_FULL_SET_DRY_RUN_CONSOLIDATED_AUDIT_ONLY_LIVE_BLOCKED`

17N must show:

- dry-run chain consolidated true
- loaded dry-run rows 309
- open gap `EXECUTABLE_PARITY_NOT_IMPLEMENTED_OR_APPROVED`
- live evaluator false
- final signal false
- all external actions false

## Gap categories

17O should identify gaps without fixing them:

- `TIER2_ROW_LEVEL_SOURCE_IDENTITY_GAP`: TIER2 is still represented as a 13L summary-chain reference, not row-level executable source identities.
- `RANGE96_EXECUTABLE_PREDICATE_GAP`: RANGE96 source rows are identity-frozen, but executable predicate parity is not implemented.
- `VOL_TRMEAN32_EXECUTABLE_PREDICATE_GAP`: VOL source rows are identity-frozen, but executable predicate parity is not implemented.
- `FULL_SET_ARBITRATION_EXECUTION_GAP`: identity-only rows do not yet define executable MEDIUM arbitration behavior.
- `LIVE_PARITY_AND_SAFETY_GATE_GAP`: no live evaluator, final signal, Discord, MT5, AI, or live-hook permission exists.

## Output folder

`FX_OUTPUTS/gold_v2_17o_medium_full_set_executable_parity_gap_analysis_audit_only`

## Main outputs

- `GOLD_V2_17O_MEDIUM_FULL_SET_EXECUTABLE_PARITY_GAP_ANALYSIS_AUDIT_ONLY_REPORT.md`
- `gold_v2_17o_medium_full_set_executable_parity_gap_analysis_summary.json`
- `gold_v2_17o_input_audit.csv`
- `gold_v2_17o_gap_analysis_checks.csv`
- `gold_v2_17o_executable_parity_gap_matrix.csv`
- `gold_v2_17o_component_gap_counts.csv`
- `gold_v2_17o_required_next_gates.csv`
- `gold_v2_17o_blockers.csv`
- `gold_v2_17o_safety_matrix.csv`

## Success status

`MEDIUM_FULL_SET_EXECUTABLE_PARITY_GAP_ANALYSIS_READY_AUDIT_ONLY_LIVE_BLOCKED`

This means the executable parity gap has been documented. It does not allow implementation, live execution, final signals, or external actions.

## Stop conditions

Stop if:

- any required input is missing,
- 17N status is not expected,
- 17N consolidation checks or safety contain STOP,
- manifest counts differ from expectations,
- any external action flag is true.

## Recommended next step after success

After 17O success, the next possible step is:

`17P_MEDIUM_FULL_SET_EXECUTABLE_PARITY_PLAN_AUDIT_ONLY`

17P must remain planning-only unless separately authorized by later audit gates.
