# GOLD V2 22G additional audit read-only final handoff spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `22G_ADDITIONAL_AUDIT_READ_ONLY_FINAL_HANDOFF_AUDIT_ONLY`
Mode: audit-only

## Purpose

22G creates the final read-only handoff after 22F.

Selected value: `REQUEST_MORE_AUDIT`.

## Required upstream status

`ADDITIONAL_AUDIT_READ_ONLY_FINAL_AUDIT_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Inputs

22F output folder:

`FX_OUTPUTS/gold_v2_22f_additional_audit_read_only_final_audit_audit_only`

Required files include 22F summary, final checks, gates, safety, and report.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_22g_additional_audit_read_only_final_handoff_audit_only`

Outputs include report, summary JSON, input audit, handoff checks, next gates, safety matrix, and final handoff note.

## Success status

`ADDITIONAL_AUDIT_READ_ONLY_FINAL_HANDOFF_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next state

`HUMAN_REVIEW_REQUEST_MORE_AUDIT_COMPLETE_AUDIT_ONLY`

No live, final, external, or recovery path is enabled by this step.
