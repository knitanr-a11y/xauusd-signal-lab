# GOLD V2 18C TIER2 source artifact inventory audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18C_TIER2_SOURCE_ARTIFACT_INVENTORY_AUDIT_ONLY`
Mode: audit-only

## Purpose

18C inventories existing audited artifacts that may help recover the missing TIER2 row-level source identity.

18C is inventory-only. It does not recover the source identity, does not reconstruct from OHLC, does not implement predicates, does not implement arbitration, does not evaluate OHLC, does not run replay, does not rediscover candidates, does not create final signals, does not send Discord notifications, does not place MT5 orders, does not call AI API, and does not install a live hook.

## Source of truth

Use audited 18B outputs:

1. `FX_OUTPUTS/gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only/gold_v2_18b_tier2_row_level_source_identity_recovery_plan_summary.json`
2. `FX_OUTPUTS/gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only/gold_v2_18b_recovery_plan_checks.csv`
3. `FX_OUTPUTS/gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only/gold_v2_18b_required_identity_fields.csv`
4. `FX_OUTPUTS/gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only/gold_v2_18b_allowed_source_artifact_classes.csv`
5. `FX_OUTPUTS/gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only/gold_v2_18b_recovery_validation_criteria.csv`
6. `FX_OUTPUTS/gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only/gold_v2_18b_stop_conditions.csv`
7. `FX_OUTPUTS/gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only/gold_v2_18b_required_next_gates.csv`
8. `FX_OUTPUTS/gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only/gold_v2_18b_blockers.csv`
9. `FX_OUTPUTS/gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only/gold_v2_18b_safety_matrix.csv`

18C may scan file names and metadata under `FX_OUTPUTS` to create an inventory. It must not infer a recovered row-level identity from OHLC or approximate reconstruction.

## Expected input state

18B must have status:

`TIER2_ROW_LEVEL_SOURCE_IDENTITY_RECOVERY_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED`

Expected 18B state:

- recovery plan ready true
- required identity fields 10
- allowed source artifact classes 5
- validation criteria 6
- source recovery executed false
- implementation allowed false
- OHLC replay allowed false
- live enabled false
- final signal false
- all external actions false
- NO_SIGNAL Discord notification false

## Inventory policy

18C may record candidate file metadata such as path, filename, suffix, size, sha256, and classification.

18C must not:

- recover the TIER2 identity,
- synthesize source rows,
- reconstruct from OHLC,
- treat summary-chain-only references as row-level identity,
- enable implementation, replay, live, final, or external actions.

## Output folder

`FX_OUTPUTS/gold_v2_18c_tier2_source_artifact_inventory_audit_only`

## Main outputs

- `GOLD_V2_18C_TIER2_SOURCE_ARTIFACT_INVENTORY_AUDIT_ONLY_REPORT.md`
- `gold_v2_18c_tier2_source_artifact_inventory_summary.json`
- `gold_v2_18c_input_audit.csv`
- `gold_v2_18c_inventory_checks.csv`
- `gold_v2_18c_tier2_source_artifact_inventory.csv`
- `gold_v2_18c_candidate_review_plan.csv`
- `gold_v2_18c_required_next_gates.csv`
- `gold_v2_18c_blockers.csv`
- `gold_v2_18c_safety_matrix.csv`

## Success status

`TIER2_SOURCE_ARTIFACT_INVENTORY_READY_AUDIT_ONLY_LIVE_BLOCKED`

This means an inventory exists. It does not mean the TIER2 row-level source identity has been recovered.

## Stop conditions

Stop if:

- any required input is missing,
- 18B status is not expected,
- 18B checks or safety contain STOP,
- source recovery has already been executed in 18B,
- any inventory or review row enables implementation/live/final/external actions,
- NO_SIGNAL Discord notification is true.

## Recommended next step after success

After 18C success, the next possible step is:

`18D_TIER2_SOURCE_ARTIFACT_CANDIDATE_REVIEW_AUDIT_ONLY`

18D must remain review/audit-only and must not perform approximate reconstruction or executable implementation.
