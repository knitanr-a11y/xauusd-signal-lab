# GOLD V2 20Y selected value draft reconciliation spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20Y_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_RECONCILIATION_AUDIT_ONLY`
Mode: audit-only

## Purpose

20Y reconciles the 20V/20W/20X selected-value chain.

Selected value: `REQUEST_MORE_AUDIT`.

Meaning: additional audit is requested. This is not source recovery approval.

## Required upstream status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_CONTENT_AUDIT_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Inputs

- 20X summary/checks/gates/safety/report
- 20W summary/load audit
- 20V selected value draft
- `docs/gold_v2/GOLD_V2_20Y_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20y_tier2_source_identity_human_decision_selected_value_draft_reconciliation_audit_only`

Outputs include report, summary JSON, input audit, stage status audit, reconciliation checks, next gates, and safety matrix.

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_RECONCILIATION_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next state

`20Z_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_FINAL_AUDIT_AUDIT_ONLY`

20Y keeps source recovery, finalization, live, final signal, Discord, MT5, AI API, and live hook blocked.
