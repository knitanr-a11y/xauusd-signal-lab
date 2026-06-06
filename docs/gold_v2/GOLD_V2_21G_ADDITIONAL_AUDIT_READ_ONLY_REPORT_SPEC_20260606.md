# GOLD V2 21G additional audit read-only report spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `21G_ADDITIONAL_AUDIT_READ_ONLY_REPORT_AUDIT_ONLY`
Mode: audit-only

## Purpose

21G creates a read-only report after 21F.

Selected value: `REQUEST_MORE_AUDIT`.

## Required upstream status

`ADDITIONAL_AUDIT_SCOPE_FINAL_AUDIT_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Inputs

21F output folder:

`FX_OUTPUTS/gold_v2_21f_additional_audit_scope_final_audit_audit_only`

Required files include 21F summary, final checks, gates, safety, and report.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_21g_additional_audit_read_only_report_audit_only`

Outputs include report, summary JSON, input audit, report checks, next gates, and safety matrix.

## Success status

`ADDITIONAL_AUDIT_READ_ONLY_REPORT_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next state

`21H_ADDITIONAL_AUDIT_HANDOFF_AUDIT_ONLY`

No live, final, external, or recovery path is enabled by this step.
