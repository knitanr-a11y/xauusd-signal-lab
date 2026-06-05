# GOLD V2 18L TIER2 source identity dry-run load smoke audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18L_TIER2_SOURCE_IDENTITY_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY`
Mode: audit-only

## Purpose

18L validates that the 18K dry-run outputs can be loaded and that all audit-only safety constraints remain intact.

18L does not promote any 18K output to source-of-truth. The 18K ledger remains a dry-run candidate identity ledger only.

## Inputs

Use only 18K outputs from:

`FX_OUTPUTS/gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only`

Required inputs:

- `gold_v2_18k_tier2_source_identity_dry_run_implementation_summary.json`
- `gold_v2_18k_input_audit.csv`
- `gold_v2_18k_implementation_checks.csv`
- `gold_v2_18k_dry_run_candidate_identity_rows.csv`
- `gold_v2_18k_artifact_row_counts.csv`
- `gold_v2_18k_dry_run_field_derivation_audit.csv`
- `gold_v2_18k_dry_run_validation_checks.csv`
- `gold_v2_18k_required_next_gates.csv`
- `gold_v2_18k_blockers.csv`
- `gold_v2_18k_safety_matrix.csv`
- `GOLD_V2_18K_TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY_REPORT.md`

Expected upstream status:

`TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## Checks

18L checks:

- required files exist and load
- 18K status matches the expected upstream status
- implementation and validation STOP rows are zero
- 18K safety STOP rows are zero
- source artifact count is 5
- expected rows, actual rows, and ledger rows are all 104
- required ledger columns exist
- ledger label remains `DRY_RUN_CANDIDATE_IDENTITY_LEDGER_NOT_SOURCE_OF_TRUTH`
- ledger status remains `DRY_RUN_CANDIDATE_ONLY_NOT_SOURCE_OF_TRUTH`
- row hashes exist and use the dry-run hash prefix
- source recovery, identity finalization, and identity recovered flags remain false
- live/final/external action flags remain false
- field derivation audit has zero STOP rows
- source finalization, source recovery, live, and final gates remain blocked after 18K

## Output folder

`FX_OUTPUTS/gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only`

## Outputs

- `GOLD_V2_18L_TIER2_SOURCE_IDENTITY_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY_REPORT.md`
- `gold_v2_18l_tier2_source_identity_dry_run_load_smoke_summary.json`
- `gold_v2_18l_input_audit.csv`
- `gold_v2_18l_load_checks.csv`
- `gold_v2_18l_ledger_column_audit.csv`
- `gold_v2_18l_ledger_safety_audit.csv`
- `gold_v2_18l_row_count_audit.csv`
- `gold_v2_18l_required_next_gates.csv`
- `gold_v2_18l_blockers.csv`
- `gold_v2_18l_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_DRY_RUN_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This status means only that the 18K files passed load-smoke checks. It is not source recovery, final identity, source-of-truth acceptance, live readiness, or final signal readiness.

## Required next gate

`18M_TIER2_SOURCE_IDENTITY_DRY_RUN_CONTENT_AUDIT_ONLY`

18M may inspect ledger content more deeply, still audit-only.

## Execution order

1. Confirm 18K outputs exist.
2. Execute the 18L Python audit script from the repository root.
3. Review load checks, ledger column audit, ledger safety audit, safety matrix, summary, and report.

## Stop conditions

18L stops if inputs are missing, load fails, counts differ from 18K, required columns are missing, any forbidden safety flag becomes true, any STOP row exists, or the ledger is marked source-of-truth.

## Do not use yet

The 18K dry-run candidate identity ledger remains not source-of-truth after 18L. Do not use it for final signals, live parity, source recovery, or identity finalization.
