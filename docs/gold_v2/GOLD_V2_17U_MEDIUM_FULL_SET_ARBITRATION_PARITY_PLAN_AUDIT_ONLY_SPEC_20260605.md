# GOLD V2 17U MEDIUM full-set arbitration parity plan audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17U_MEDIUM_FULL_SET_ARBITRATION_PARITY_PLAN_AUDIT_ONLY`
Mode: audit-only

## Purpose

17U consolidates the component source-mapping results and writes a planning-only roadmap for any future MEDIUM full-set arbitration parity work.

17U does not implement arbitration, does not implement predicates, does not evaluate OHLC, does not rediscover candidates, does not create final signals, does not send Discord notifications, does not place MT5 orders, does not call AI API, and does not install a live hook.

## Source of truth

Use only audited outputs from 17R/17S/17T and the 17G manifest:

1. `FX_OUTPUTS/gold_v2_17t_vol_trmean32_predicate_source_mapping_audit_only/gold_v2_17t_vol_trmean32_predicate_source_mapping_summary.json`
2. `FX_OUTPUTS/gold_v2_17t_vol_trmean32_predicate_source_mapping_audit_only/gold_v2_17t_vol_trmean32_source_mapping_checks.csv`
3. `FX_OUTPUTS/gold_v2_17t_vol_trmean32_predicate_source_mapping_audit_only/gold_v2_17t_vol_trmean32_required_source_artifacts.csv`
4. `FX_OUTPUTS/gold_v2_17t_vol_trmean32_predicate_source_mapping_audit_only/gold_v2_17t_required_next_gates.csv`
5. `FX_OUTPUTS/gold_v2_17t_vol_trmean32_predicate_source_mapping_audit_only/gold_v2_17t_safety_matrix.csv`
6. `FX_OUTPUTS/gold_v2_17s_range96_predicate_source_mapping_audit_only/gold_v2_17s_range96_predicate_source_mapping_summary.json`
7. `FX_OUTPUTS/gold_v2_17r_tier2_row_level_source_mapping_audit_only/gold_v2_17r_tier2_row_level_source_mapping_summary.json`
8. `FX_OUTPUTS/gold_v2_17g_medium_full_set_candidate_mapping_audit_only/gold_v2_17g_full_set_candidate_manifest.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer executable predicates.

## Expected input state

17T must have status:

`VOL_TRMEAN32_PREDICATE_SOURCE_MAPPING_READY_AUDIT_ONLY_LIVE_BLOCKED`

Expected source-mapping state:

- TIER2 row-level source identity gap remains confirmed.
- RANGE96 source mapping is ready, but predicate implementation is not allowed.
- VOL_TRMEAN32 source mapping is ready, but predicate implementation is not allowed.
- MEDIUM full-set arbitration parity remains a planning-only topic.
- All live/final/external action flags remain false.

Expected manifest counts:

- `TIER2_HVT`: 1
- `RANGE96_REFINED`: 168
- `VOL_TRMEAN32_REFINED`: 140
- total: 309

## Output folder

`FX_OUTPUTS/gold_v2_17u_medium_full_set_arbitration_parity_plan_audit_only`

## Main outputs

- `GOLD_V2_17U_MEDIUM_FULL_SET_ARBITRATION_PARITY_PLAN_AUDIT_ONLY_REPORT.md`
- `gold_v2_17u_medium_full_set_arbitration_parity_plan_summary.json`
- `gold_v2_17u_input_audit.csv`
- `gold_v2_17u_arbitration_plan_checks.csv`
- `gold_v2_17u_component_dependency_matrix.csv`
- `gold_v2_17u_arbitration_parity_plan.csv`
- `gold_v2_17u_planned_stop_conditions.csv`
- `gold_v2_17u_required_next_gates.csv`
- `gold_v2_17u_blockers.csv`
- `gold_v2_17u_safety_matrix.csv`

## Success status

`MEDIUM_FULL_SET_ARBITRATION_PARITY_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED`

This means an arbitration parity plan exists. It does not permit implementation, live execution, final signals, or external actions.

## Stop conditions

Stop if:

- any required input is missing,
- 17T status is not expected,
- 17T checks or safety contain STOP,
- component manifest counts differ from expectations,
- any plan row enables implementation/live/final/external actions.

## Recommended next step after success

After 17U success, the next possible step is:

`17V_LIVE_PARITY_SAFETY_GATE_PLAN_AUDIT_ONLY`

17V must remain planning/audit-only and must not enable live execution or final signals.
