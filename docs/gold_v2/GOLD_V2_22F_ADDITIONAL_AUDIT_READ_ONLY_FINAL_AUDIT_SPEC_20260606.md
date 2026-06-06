# GOLD V2 22F additional audit read-only final audit spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `22F_ADDITIONAL_AUDIT_READ_ONLY_FINAL_AUDIT_AUDIT_ONLY`
Mode: audit-only

## Purpose

22F final-audits the read-only additional audit chain after 22E.

Selected value: `REQUEST_MORE_AUDIT`.

## Required upstream status

`ADDITIONAL_AUDIT_READ_ONLY_SCOPE_RECONCILIATION_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Inputs

22E output folder:

`FX_OUTPUTS/gold_v2_22e_additional_audit_read_only_scope_reconciliation_audit_only`

Required files include 22E summary, scope reconciliation, reconciliation checks, gates, safety, and report.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_22f_additional_audit_read_only_final_audit_audit_only`

Outputs include report, summary JSON, input audit, final checks, next gates, and safety matrix.

## Success status

`ADDITIONAL_AUDIT_READ_ONLY_FINAL_AUDIT_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next state

`22G_ADDITIONAL_AUDIT_READ_ONLY_FINAL_HANDOFF_AUDIT_ONLY`

No live, final, external, or recovery path is enabled by this step.
