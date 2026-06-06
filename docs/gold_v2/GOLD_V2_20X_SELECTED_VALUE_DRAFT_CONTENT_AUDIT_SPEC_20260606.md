# GOLD V2 20X selected value draft content audit spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20X_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_CONTENT_AUDIT_AUDIT_ONLY`
Mode: audit-only

## Purpose

20X content-audits the loaded selected-value draft chain after 20W passed.

20X verifies that `REQUEST_MORE_AUDIT` means additional audit is requested and source recovery is not approved.

## Required upstream status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_LOAD_SMOKE_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Inputs

20W folder:

`FX_OUTPUTS/gold_v2_20w_tier2_source_identity_human_decision_selected_value_draft_load_smoke_audit_only`

Required files:

- `gold_v2_20w_tier2_source_identity_human_decision_selected_value_draft_load_smoke_summary.json`
- `gold_v2_20w_draft_load_audit.csv`
- `gold_v2_20w_load_checks.csv`
- `gold_v2_20w_required_next_gates.csv`
- `gold_v2_20w_safety_matrix.csv`
- `GOLD_V2_20W_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`

20V folder:

`FX_OUTPUTS/gold_v2_20v_tier2_source_identity_human_decision_selected_value_draft_audit_only`

Required file:

- `gold_v2_20v_selected_value_draft.json`

Backup manifest:

- `docs/gold_v2/GOLD_V2_20X_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20x_tier2_source_identity_human_decision_selected_value_draft_content_audit_audit_only`

Outputs:

- `GOLD_V2_20X_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_CONTENT_AUDIT_AUDIT_ONLY_REPORT.md`
- `gold_v2_20x_tier2_source_identity_human_decision_selected_value_draft_content_audit_summary.json`
- `gold_v2_20x_input_audit.csv`
- `gold_v2_20x_content_checks.csv`
- `gold_v2_20x_required_next_gates.csv`
- `gold_v2_20x_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_CONTENT_AUDIT_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next state

`20Y_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_RECONCILIATION_AUDIT_ONLY`

20X still blocks source recovery, finalization, live, final signal, Discord, MT5, AI API, and live hook.
