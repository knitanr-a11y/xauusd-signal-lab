# GOLD V2 20Z selected value final audit spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20Z_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_FINAL_AUDIT_AUDIT_ONLY`
Mode: audit-only

## Purpose

20Z final-audits the reconciled selected-value chain.

Selected value: `REQUEST_MORE_AUDIT`.

Meaning: additional audit is requested. This is not source recovery approval.

## Required upstream status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_RECONCILIATION_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Inputs

- 20Y summary/checks/stage/gates/safety/report
- `docs/gold_v2/GOLD_V2_20Z_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20z_tier2_source_identity_human_decision_selected_value_final_audit_audit_only`

Outputs include report, summary JSON, input audit, final checks, next gates, and safety matrix.

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_FINAL_AUDIT_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_ADDITIONAL_AUDIT_REQUIRED_SOURCE_RECOVERY_STILL_BLOCKED`

## Next state

`21A_ADDITIONAL_AUDIT_PLANNING_AUDIT_ONLY`

20Z keeps source recovery, finalization, live, final signal, Discord, MT5, AI API, and live hook blocked.
