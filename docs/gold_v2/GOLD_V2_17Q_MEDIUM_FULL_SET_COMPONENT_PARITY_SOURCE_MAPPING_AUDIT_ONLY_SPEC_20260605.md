# GOLD V2 17Q MEDIUM full-set component parity source mapping audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17Q_MEDIUM_FULL_SET_COMPONENT_PARITY_SOURCE_MAPPING_AUDIT_ONLY`
Mode: audit-only

## Purpose

17Q maps each executable parity gap from 17P to the source artifact class that must be audited before any future executable parity implementation can be discussed.

17Q is source mapping only. It does not implement predicates, does not evaluate OHLC, does not rediscover candidates, does not create final signals, does not send Discord notifications, does not place MT5 orders, does not call AI API, and does not install a live hook.

## Source of truth

Use only 17P audited outputs and the already audited 17G manifest for row-count context:

1. `FX_OUTPUTS/gold_v2_17p_medium_full_set_executable_parity_plan_audit_only/gold_v2_17p_medium_full_set_executable_parity_plan_summary.json`
2. `FX_OUTPUTS/gold_v2_17p_medium_full_set_executable_parity_plan_audit_only/gold_v2_17p_plan_checks.csv`
3. `FX_OUTPUTS/gold_v2_17p_medium_full_set_executable_parity_plan_audit_only/gold_v2_17p_component_parity_plan.csv`
4. `FX_OUTPUTS/gold_v2_17p_medium_full_set_executable_parity_plan_audit_only/gold_v2_17p_gap_to_next_step_map.csv`
5. `FX_OUTPUTS/gold_v2_17p_medium_full_set_executable_parity_plan_audit_only/gold_v2_17p_planned_stop_conditions.csv`
6. `FX_OUTPUTS/gold_v2_17p_medium_full_set_executable_parity_plan_audit_only/gold_v2_17p_required_next_gates.csv`
7. `FX_OUTPUTS/gold_v2_17p_medium_full_set_executable_parity_plan_audit_only/gold_v2_17p_safety_matrix.csv`
8. `FX_OUTPUTS/gold_v2_17g_medium_full_set_candidate_mapping_audit_only/gold_v2_17g_full_set_candidate_manifest.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer executable predicates.

## Expected input state

17P must have status:

`MEDIUM_FULL_SET_EXECUTABLE_PARITY_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED`

Expected 17P state:

- parity plan ready true
- gap count 5
- executable parity implemented false
- dry-run execution false
- live evaluator false
- final signal false
- all external actions false

## Mapping policy

17Q maps only the required source artifact class for each gap:

- TIER2 must require audited row-level TIER2 source identity before executable parity.
- RANGE96 must require audited predicate source mapping before executable parity.
- VOL_TRMEAN32 must require audited predicate source mapping before executable parity.
- MEDIUM full-set arbitration must require component parity completion first.
- Live parity/safety must require explicit later safety gates.

No mapping row may mark implementation, live evaluator, final signal, Discord, MT5, AI API, or live hook as allowed.

## Output folder

`FX_OUTPUTS/gold_v2_17q_medium_full_set_component_parity_source_mapping_audit_only`

## Main outputs

- `GOLD_V2_17Q_MEDIUM_FULL_SET_COMPONENT_PARITY_SOURCE_MAPPING_AUDIT_ONLY_REPORT.md`
- `gold_v2_17q_medium_full_set_component_parity_source_mapping_summary.json`
- `gold_v2_17q_input_audit.csv`
- `gold_v2_17q_source_mapping_checks.csv`
- `gold_v2_17q_component_source_mapping_matrix.csv`
- `gold_v2_17q_source_artifact_requirements.csv`
- `gold_v2_17q_required_next_gates.csv`
- `gold_v2_17q_blockers.csv`
- `gold_v2_17q_safety_matrix.csv`

## Success status

`MEDIUM_FULL_SET_COMPONENT_PARITY_SOURCE_MAPPING_READY_AUDIT_ONLY_LIVE_BLOCKED`

This means source mapping exists. It does not permit predicate implementation, live execution, final signals, or external actions.

## Stop conditions

Stop if:

- any required 17P/17G artifact is missing,
- 17P status is not expected,
- 17P checks or safety contain STOP,
- expected gap rows are missing,
- manifest counts differ from expectations,
- any mapping row enables implementation/live/final/external actions.

## Recommended next step after success

After 17Q success, the next possible step is:

`17R_TIER2_ROW_LEVEL_SOURCE_MAPPING_AUDIT_ONLY`

17R must remain source-mapping/audit-only and must not implement executable predicates.
