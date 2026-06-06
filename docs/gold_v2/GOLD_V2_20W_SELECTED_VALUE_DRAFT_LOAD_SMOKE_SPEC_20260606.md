# GOLD V2 20W selected value draft load-smoke spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `20W_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_LOAD_SMOKE_AUDIT_ONLY`
Mode: audit-only

## Purpose

20W load-smokes the 20V selected-value draft artifact.

20W verifies that the selected value is `REQUEST_MORE_AUDIT`, that the draft is not source recovery approval, and that all downstream source/live/external actions remain blocked.

## Required upstream status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Inputs

20V folder:

`FX_OUTPUTS/gold_v2_20v_tier2_source_identity_human_decision_selected_value_draft_audit_only`

Required files:

- `gold_v2_20v_tier2_source_identity_human_decision_selected_value_draft_summary.json`
- `gold_v2_20v_selected_value_draft.json`
- `gold_v2_20v_draft_checks.csv`
- `gold_v2_20v_required_next_gates.csv`
- `gold_v2_20v_safety_matrix.csv`
- `GOLD_V2_20V_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_AUDIT_ONLY_REPORT.md`

Backup manifest:

- `docs/gold_v2/GOLD_V2_20W_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_20w_tier2_source_identity_human_decision_selected_value_draft_load_smoke_audit_only`

Outputs:

- `GOLD_V2_20W_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`
- `gold_v2_20w_tier2_source_identity_human_decision_selected_value_draft_load_smoke_summary.json`
- `gold_v2_20w_input_audit.csv`
- `gold_v2_20w_draft_load_audit.csv`
- `gold_v2_20w_load_checks.csv`
- `gold_v2_20w_required_next_gates.csv`
- `gold_v2_20w_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_LOAD_SMOKE_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next state

`20X_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_CONTENT_AUDIT_AUDIT_ONLY`

20W still blocks source recovery, finalization, live, final signal, Discord, MT5, AI API, and live hook.
