# GOLD V2 17T VOL_TRMEAN32 predicate source mapping audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17T_VOL_TRMEAN32_PREDICATE_SOURCE_MAPPING_AUDIT_ONLY`
Mode: audit-only

## Purpose

17T audits the `VOL_TRMEAN32_REFINED` source rows that would be required before any future executable predicate parity discussion.

17T is predicate source mapping only. It does not implement predicates, does not evaluate OHLC, does not rediscover candidates, does not create final signals, does not send Discord notifications, does not place MT5 orders, does not call AI API, and does not install a live hook.

## Source of truth

Use only 17S audited outputs and the already audited 17G manifest:

1. `FX_OUTPUTS/gold_v2_17s_range96_predicate_source_mapping_audit_only/gold_v2_17s_range96_predicate_source_mapping_summary.json`
2. `FX_OUTPUTS/gold_v2_17s_range96_predicate_source_mapping_audit_only/gold_v2_17s_range96_source_mapping_checks.csv`
3. `FX_OUTPUTS/gold_v2_17s_range96_predicate_source_mapping_audit_only/gold_v2_17s_required_next_gates.csv`
4. `FX_OUTPUTS/gold_v2_17s_range96_predicate_source_mapping_audit_only/gold_v2_17s_safety_matrix.csv`
5. `FX_OUTPUTS/gold_v2_17g_medium_full_set_candidate_mapping_audit_only/gold_v2_17g_full_set_candidate_manifest.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer executable predicates.

## Expected input state

17S must have status:

`RANGE96_PREDICATE_SOURCE_MAPPING_READY_AUDIT_ONLY_LIVE_BLOCKED`

Expected 17S state:

- RANGE96 predicate source mapping ready true
- RANGE96 manifest rows 168
- predicate implementation allowed false
- executable parity implemented false
- dry-run execution false
- live evaluator false
- final signal false
- all external actions false

Expected VOL manifest state:

- `VOL_TRMEAN32_REFINED` rows: 140
- required source identity columns present
- all VOL rows remain non-executable and non-final

## Output folder

`FX_OUTPUTS/gold_v2_17t_vol_trmean32_predicate_source_mapping_audit_only`

## Main outputs

- `GOLD_V2_17T_VOL_TRMEAN32_PREDICATE_SOURCE_MAPPING_AUDIT_ONLY_REPORT.md`
- `gold_v2_17t_vol_trmean32_predicate_source_mapping_summary.json`
- `gold_v2_17t_input_audit.csv`
- `gold_v2_17t_vol_trmean32_source_mapping_checks.csv`
- `gold_v2_17t_vol_trmean32_current_identity_rows.csv`
- `gold_v2_17t_vol_trmean32_required_source_artifacts.csv`
- `gold_v2_17t_required_next_gates.csv`
- `gold_v2_17t_blockers.csv`
- `gold_v2_17t_safety_matrix.csv`

## Success status

`VOL_TRMEAN32_PREDICATE_SOURCE_MAPPING_READY_AUDIT_ONLY_LIVE_BLOCKED`

This means VOL_TRMEAN32 predicate source mapping is audit-ready. It does not permit predicate implementation, live execution, final signals, or external actions.

## Stop conditions

Stop if:

- any required input is missing,
- 17S status is not expected,
- 17S checks or safety contain STOP,
- `VOL_TRMEAN32_REFINED` manifest row count is not 140,
- required manifest columns are missing,
- any VOL mapping row enables predicate/live/final/external actions.

## Recommended next step after success

After 17T success, the next possible step is:

`17U_MEDIUM_FULL_SET_ARBITRATION_PARITY_PLAN_AUDIT_ONLY`

17U must remain planning/audit-only and must not implement executable predicates, live execution, or final signals.
