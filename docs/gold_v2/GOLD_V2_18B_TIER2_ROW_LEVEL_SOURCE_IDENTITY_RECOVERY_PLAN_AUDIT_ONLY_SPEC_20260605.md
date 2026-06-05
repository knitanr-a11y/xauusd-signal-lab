# GOLD V2 18B TIER2 row-level source identity recovery plan audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18B_TIER2_ROW_LEVEL_SOURCE_IDENTITY_RECOVERY_PLAN_AUDIT_ONLY`
Mode: audit-only

## Purpose

18B plans how to recover the missing TIER2 row-level source identity required before any executable parity work.

18B is recovery planning only. It does not recover files, does not implement predicates, does not implement arbitration, does not evaluate OHLC, does not run replay, does not rediscover candidates, does not create final signals, does not send Discord notifications, does not place MT5 orders, does not call AI API, and does not install a live hook.

## Source of truth

Use only audited 18A outputs:

1. `FX_OUTPUTS/gold_v2_18a_executable_parity_design_audit_only/gold_v2_18a_executable_parity_design_summary.json`
2. `FX_OUTPUTS/gold_v2_18a_executable_parity_design_audit_only/gold_v2_18a_design_checks.csv`
3. `FX_OUTPUTS/gold_v2_18a_executable_parity_design_audit_only/gold_v2_18a_component_parity_design_matrix.csv`
4. `FX_OUTPUTS/gold_v2_18a_executable_parity_design_audit_only/gold_v2_18a_acceptance_criteria.csv`
5. `FX_OUTPUTS/gold_v2_18a_executable_parity_design_audit_only/gold_v2_18a_stop_conditions.csv`
6. `FX_OUTPUTS/gold_v2_18a_executable_parity_design_audit_only/gold_v2_18a_required_next_gates.csv`
7. `FX_OUTPUTS/gold_v2_18a_executable_parity_design_audit_only/gold_v2_18a_blockers.csv`
8. `FX_OUTPUTS/gold_v2_18a_executable_parity_design_audit_only/gold_v2_18a_safety_matrix.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer executable predicates.

## Expected input state

18A must have status:

`EXECUTABLE_PARITY_DESIGN_READY_AUDIT_ONLY_LIVE_BLOCKED`

Expected 18A state:

- executable parity design ready true
- component design rows 4
- arbitration design rows 5
- acceptance criteria rows 5
- open blockers carried forward 4
- implementation allowed false
- OHLC replay allowed false
- live enabled false
- live evaluator false
- final signal false
- all external actions false
- NO_SIGNAL Discord notification false

## Recovery planning policy

18B must plan recovery of TIER2 row-level source identity without performing recovery:

1. Identify required row-level identity fields.
2. Identify allowed source artifact classes to search in a later audit-only inventory step.
3. Define validation criteria for a recovered TIER2 row-level identity artifact.
4. Define stop conditions for missing, ambiguous, approximate, or reconstructed sources.
5. Carry forward all safety non-enablement flags.

No recovery plan row may mark implementation/live/final/external actions as allowed.

## Output folder

`FX_OUTPUTS/gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only`

## Main outputs

- `GOLD_V2_18B_TIER2_ROW_LEVEL_SOURCE_IDENTITY_RECOVERY_PLAN_AUDIT_ONLY_REPORT.md`
- `gold_v2_18b_tier2_row_level_source_identity_recovery_plan_summary.json`
- `gold_v2_18b_input_audit.csv`
- `gold_v2_18b_recovery_plan_checks.csv`
- `gold_v2_18b_required_identity_fields.csv`
- `gold_v2_18b_allowed_source_artifact_classes.csv`
- `gold_v2_18b_recovery_validation_criteria.csv`
- `gold_v2_18b_stop_conditions.csv`
- `gold_v2_18b_required_next_gates.csv`
- `gold_v2_18b_blockers.csv`
- `gold_v2_18b_safety_matrix.csv`

## Success status

`TIER2_ROW_LEVEL_SOURCE_IDENTITY_RECOVERY_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED`

This means the TIER2 recovery plan exists. It does not permit source recovery execution, predicate implementation, replay, live execution, final signals, or external actions.

## Stop conditions

Stop if:

- any required input is missing,
- 18A status is not expected,
- 18A checks or safety contain STOP,
- TIER2 row-level identity blocker is not carried forward,
- any recovery row enables implementation/live/final/external actions,
- NO_SIGNAL Discord notification is true.

## Recommended next step after success

After 18B success, the next possible step is:

`18C_TIER2_SOURCE_ARTIFACT_INVENTORY_AUDIT_ONLY`

18C must remain inventory/audit-only and must not perform approximate reconstruction or executable implementation.
