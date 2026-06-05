# GOLD V2 17P MEDIUM full-set executable parity plan audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17P_MEDIUM_FULL_SET_EXECUTABLE_PARITY_PLAN_AUDIT_ONLY`
Mode: audit-only

## Purpose

17P writes a planning-only roadmap for closing the executable parity gaps identified by 17O.

17P does not implement predicates, does not evaluate OHLC, does not rediscover candidates, does not create final signals, does not send Discord notifications, does not place MT5 orders, does not call AI API, and does not install a live hook.

## Source of truth

Use only 17O audited outputs:

1. `FX_OUTPUTS/gold_v2_17o_medium_full_set_executable_parity_gap_analysis_audit_only/gold_v2_17o_medium_full_set_executable_parity_gap_analysis_summary.json`
2. `FX_OUTPUTS/gold_v2_17o_medium_full_set_executable_parity_gap_analysis_audit_only/gold_v2_17o_gap_analysis_checks.csv`
3. `FX_OUTPUTS/gold_v2_17o_medium_full_set_executable_parity_gap_analysis_audit_only/gold_v2_17o_executable_parity_gap_matrix.csv`
4. `FX_OUTPUTS/gold_v2_17o_medium_full_set_executable_parity_gap_analysis_audit_only/gold_v2_17o_component_gap_counts.csv`
5. `FX_OUTPUTS/gold_v2_17o_medium_full_set_executable_parity_gap_analysis_audit_only/gold_v2_17o_required_next_gates.csv`
6. `FX_OUTPUTS/gold_v2_17o_medium_full_set_executable_parity_gap_analysis_audit_only/gold_v2_17o_safety_matrix.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer executable predicates.

## Expected input state

17O must have status:

`MEDIUM_FULL_SET_EXECUTABLE_PARITY_GAP_ANALYSIS_READY_AUDIT_ONLY_LIVE_BLOCKED`

Expected 17O state:

- gap analysis ready true
- open gap `EXECUTABLE_PARITY_NOT_IMPLEMENTED_OR_APPROVED`
- gap count 5
- affected manifest rows 309
- executable parity implemented false
- dry-run execution false
- live evaluator false
- final signal false
- all external actions false

## Planning outputs

17P writes planning-only artifacts:

- component parity plan
- gap-to-next-step mapping
- parity work ordering
- planned stop conditions
- required next gates

The first allowed follow-up after 17P is source mapping, not implementation:

`17Q_MEDIUM_FULL_SET_COMPONENT_PARITY_SOURCE_MAPPING_AUDIT_ONLY`

## Output folder

`FX_OUTPUTS/gold_v2_17p_medium_full_set_executable_parity_plan_audit_only`

## Main outputs

- `GOLD_V2_17P_MEDIUM_FULL_SET_EXECUTABLE_PARITY_PLAN_AUDIT_ONLY_REPORT.md`
- `gold_v2_17p_medium_full_set_executable_parity_plan_summary.json`
- `gold_v2_17p_input_audit.csv`
- `gold_v2_17p_plan_checks.csv`
- `gold_v2_17p_component_parity_plan.csv`
- `gold_v2_17p_gap_to_next_step_map.csv`
- `gold_v2_17p_planned_stop_conditions.csv`
- `gold_v2_17p_required_next_gates.csv`
- `gold_v2_17p_blockers.csv`
- `gold_v2_17p_safety_matrix.csv`

## Success status

`MEDIUM_FULL_SET_EXECUTABLE_PARITY_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED`

This means a plan exists. It does not permit implementation, live execution, final signals, or external actions.

## Stop conditions

Stop if:

- any required 17O artifact is missing,
- 17O status is not expected,
- 17O checks or safety contain STOP,
- gap matrix does not contain the expected five gap IDs,
- any planned next step enables implementation/live/final/external actions.

## Recommended next step after success

After 17P success, the next possible step is:

`17Q_MEDIUM_FULL_SET_COMPONENT_PARITY_SOURCE_MAPPING_AUDIT_ONLY`

17Q must remain audit-only and source-mapping only. It must not implement executable predicates.
