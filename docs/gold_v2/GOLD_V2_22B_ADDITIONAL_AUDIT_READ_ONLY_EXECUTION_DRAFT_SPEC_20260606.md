# GOLD V2 22B additional audit read-only execution draft spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `22B_ADDITIONAL_AUDIT_READ_ONLY_EXECUTION_DRAFT_AUDIT_ONLY`
Mode: audit-only

## Purpose

22B creates a read-only execution draft from the 22A planning rows.

Selected value: `REQUEST_MORE_AUDIT`.

## Required upstream status

`ADDITIONAL_AUDIT_READ_ONLY_PLANNING_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Inputs

22A output folder:

`FX_OUTPUTS/gold_v2_22a_additional_audit_read_only_planning_audit_only`

Required files include 22A summary, planning rows, planning checks, gates, safety, and report.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_22b_additional_audit_read_only_execution_draft_audit_only`

Outputs include report, summary JSON, input audit, execution draft CSV/JSON, draft checks, next gates, and safety matrix.

## Success status

`ADDITIONAL_AUDIT_READ_ONLY_EXECUTION_DRAFT_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Next state

`22C_ADDITIONAL_AUDIT_READ_ONLY_EXECUTION_DRAFT_LOAD_CHECK_AUDIT_ONLY`

No live, final, external, or recovery path is enabled by this step.
