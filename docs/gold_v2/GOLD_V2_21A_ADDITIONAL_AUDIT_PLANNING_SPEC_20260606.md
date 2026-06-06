# GOLD V2 21A additional audit planning spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `21A_ADDITIONAL_AUDIT_PLANNING_AUDIT_ONLY`
Mode: audit-only

## Purpose

21A creates an additional-audit plan after the selected human value chain finalized as `REQUEST_MORE_AUDIT`.

21A does not approve source recovery. It does not enable live/final/external actions.

## Required upstream status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_FINAL_AUDIT_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_ADDITIONAL_AUDIT_REQUIRED_SOURCE_RECOVERY_STILL_BLOCKED`

## Inputs

20Z folder:

`FX_OUTPUTS/gold_v2_20z_tier2_source_identity_human_decision_selected_value_final_audit_audit_only`

Required files:

- `gold_v2_20z_tier2_source_identity_human_decision_selected_value_final_audit_summary.json`
- `gold_v2_20z_final_checks.csv`
- `gold_v2_20z_required_next_gates.csv`
- `gold_v2_20z_safety_matrix.csv`
- `GOLD_V2_20Z_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_FINAL_AUDIT_AUDIT_ONLY_REPORT.md`

Backup manifest:

- `docs/gold_v2/GOLD_V2_21A_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Additional audit plan themes

21A should plan only read-only audits:

1. summarize unresolved uncertainty behind `REQUEST_MORE_AUDIT`
2. verify source recovery remains blocked
3. inspect remaining source identity evidence without recovery execution
4. define required evidence for any future explicit approval candidate
5. keep live/final/external integrations off

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_21a_additional_audit_planning_audit_only`

Outputs include report, summary JSON, input audit, additional audit plan CSV, planning checks, next gates, and safety matrix.

## Success status

`ADDITIONAL_AUDIT_PLANNING_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next state

`21B_ADDITIONAL_AUDIT_EXECUTION_DRAFT_AUDIT_ONLY`

21A keeps source recovery, finalization, live, final signal, Discord, MT5, AI API, and live hook blocked.
