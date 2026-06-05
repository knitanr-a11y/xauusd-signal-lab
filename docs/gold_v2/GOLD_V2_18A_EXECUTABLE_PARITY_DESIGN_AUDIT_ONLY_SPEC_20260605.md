# GOLD V2 18A executable parity design audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18A_EXECUTABLE_PARITY_DESIGN_AUDIT_ONLY`
Mode: audit-only

## Purpose

18A designs the executable parity requirements needed before any future implementation work. It uses the consolidated 17W roadmap as the source of truth.

18A is design-only. It does not implement predicates, does not implement arbitration, does not evaluate OHLC, does not run replay, does not rediscover candidates, does not create final signals, does not send Discord notifications, does not place MT5 orders, does not call AI API, and does not install a live hook.

## Source of truth

Use only audited 17W outputs:

1. `FX_OUTPUTS/gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation/gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation_summary.json`
2. `FX_OUTPUTS/gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation/gold_v2_17w_consolidation_checks.csv`
3. `FX_OUTPUTS/gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation/gold_v2_17w_roadmap_matrix.csv`
4. `FX_OUTPUTS/gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation/gold_v2_17w_open_blockers_consolidated.csv`
5. `FX_OUTPUTS/gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation/gold_v2_17w_required_next_gates.csv`
6. `FX_OUTPUTS/gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation/gold_v2_17w_safety_matrix.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer executable predicates.

## Expected input state

17W must have status:

`MEDIUM_FULL_SET_AUDIT_ONLY_ROADMAP_CONSOLIDATED_LIVE_BLOCKED`

Expected 17W state:

- roadmap consolidated true
- roadmap items 5
- open blockers 4
- enabled safety gates now 0
- live enabled false
- implementation allowed false
- live evaluator false
- final signal false
- all external actions false
- NO_SIGNAL Discord notification false

## Design policy

18A must define executable parity requirements without implementing them:

1. TIER2 row-level source identity requirement.
2. Component predicate parity design requirements for RANGE96, VOL_TRMEAN32, and TIER2.
3. MEDIUM arbitration parity design requirements.
4. Replay parity acceptance criteria as a design contract only.
5. Required stop conditions before any implementation stage.
6. Safety non-enablement carried forward.

No design row may mark implementation/live/final/external actions as allowed.

## Output folder

`FX_OUTPUTS/gold_v2_18a_executable_parity_design_audit_only`

## Main outputs

- `GOLD_V2_18A_EXECUTABLE_PARITY_DESIGN_AUDIT_ONLY_REPORT.md`
- `gold_v2_18a_executable_parity_design_summary.json`
- `gold_v2_18a_input_audit.csv`
- `gold_v2_18a_design_checks.csv`
- `gold_v2_18a_component_parity_design_matrix.csv`
- `gold_v2_18a_arbitration_design_matrix.csv`
- `gold_v2_18a_acceptance_criteria.csv`
- `gold_v2_18a_stop_conditions.csv`
- `gold_v2_18a_required_next_gates.csv`
- `gold_v2_18a_blockers.csv`
- `gold_v2_18a_safety_matrix.csv`

## Success status

`EXECUTABLE_PARITY_DESIGN_READY_AUDIT_ONLY_LIVE_BLOCKED`

This means design requirements exist. It does not permit implementation, replay, live execution, final signals, or external actions.

## Stop conditions

Stop if:

- any required input is missing,
- 17W status is not expected,
- 17W checks or safety contain STOP,
- open blockers from 17W are missing,
- any design row enables implementation/live/final/external actions,
- NO_SIGNAL Discord notification is true.

## Recommended next step after success

After 18A success, the next possible step is:

`18B_TIER2_ROW_LEVEL_SOURCE_IDENTITY_RECOVERY_PLAN_AUDIT_ONLY`

18B must remain recovery planning/audit-only unless explicit implementation approval is separately provided.
