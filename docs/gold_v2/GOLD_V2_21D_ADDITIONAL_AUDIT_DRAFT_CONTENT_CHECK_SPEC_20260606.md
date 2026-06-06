# GOLD V2 21D additional audit draft content check spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `21D_ADDITIONAL_AUDIT_DRAFT_CONTENT_CHECK_AUDIT_ONLY`
Mode: audit-only

## Purpose

21D checks that the 21B/21C additional audit draft content still matches the 21A read-only plan.

Selected value: `REQUEST_MORE_AUDIT`.

## Required upstream status

`ADDITIONAL_AUDIT_DRAFT_LOAD_CHECK_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Inputs

21C output folder:

`FX_OUTPUTS/gold_v2_21c_additional_audit_draft_load_check_audit_only`

21B output folder:

`FX_OUTPUTS/gold_v2_21b_additional_audit_execution_draft_audit_only`

Required files include 21C summary/checks/gates/safety/report and 21B execution draft CSV/JSON.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_21d_additional_audit_draft_content_check_audit_only`

Outputs include report, summary JSON, input audit, content checks, next gates, and safety matrix.

## Success status

`ADDITIONAL_AUDIT_DRAFT_CONTENT_CHECK_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next state

`21E_ADDITIONAL_AUDIT_SCOPE_RECONCILIATION_AUDIT_ONLY`

All live and external paths remain disabled.
