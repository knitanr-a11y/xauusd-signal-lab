# GOLD V2 18K TIER2 source identity dry-run implementation audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18K_TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY`
Mode: audit-only

## Purpose

18K implements the audit-only dry-run described by 18J.

18K may read the selected source CSV rows listed by 18J and may derive row-level candidate identity fields for audit. This is not source recovery execution, source identity recovery, or source identity finalization. The output ledger must be called a `dry-run candidate identity ledger`, not source-of-truth.

## Current upstream state to verify before implementation

18K must stop unless the 18J summary status is exactly:

`TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_PLAN_READY_AUDIT_ONLY_DRY_RUN_EXECUTION_BLOCKED`

18K must also stop unless the 18J implementation checks and 18J safety matrix have zero `STOP` rows.

## Allowed actions

18K may:

- read 18J plan outputs
- read the corrected 18I dry-run field recipe
- read selected source CSV artifacts listed by 18J
- derive dry-run candidate identity fields from existing CSV columns only
- compute dry-run candidate row hashes for audit comparison only
- write audit-only CSV/JSON/MD outputs

## Forbidden actions

18K must not:

- execute source recovery
- finalize source identity
- mark source identity recovered
- call the dry-run ledger source-of-truth
- update manifests or rule definitions
- implement predicates or arbitration for live/final
- replay or reconstruct from OHLC
- produce final MEDIUM signals
- enable live evaluator, final signal, or live hooks
- send Discord notifications
- send NO_SIGNAL Discord notifications
- place MT5 orders
- call AI APIs

## Inputs

Use these 18J outputs from:

`FX_OUTPUTS/gold_v2_18j_tier2_source_identity_dry_run_implementation_plan_audit_only`

- `gold_v2_18j_tier2_source_identity_dry_run_implementation_plan_summary.json`
- `gold_v2_18j_plan_checks.csv`
- `gold_v2_18j_planned_artifacts.csv`
- `gold_v2_18j_planned_processing_steps.csv`
- `gold_v2_18j_planned_output_contract.csv`
- `gold_v2_18j_planned_stop_conditions.csv`
- `gold_v2_18j_required_next_gates.csv`
- `gold_v2_18j_blockers.csv`
- `gold_v2_18j_safety_matrix.csv`

Use this corrected 18I recipe from:

`FX_OUTPUTS/gold_v2_18i_tier2_source_identity_extraction_dry_run_design_audit_only`

- `gold_v2_18i_dry_run_field_recipe.csv`

Use the selected candidate source CSV artifacts listed by 18J. The current 18J plan expects these rows:

| role | input CSV | expected rows |
|---|---|---:|
| PRIMARY | `gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only\gold_v2_13d2_tier2_source_rows.csv` | 31 |
| BACKUP | `gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only\gold_v2_13d3_tier2_source_rows_with_reconciled_match.csv` | 31 |
| BACKUP | `gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only\gold_v2_13d2_tier2_final_manifest_mismatch_rows.csv` | 11 |
| BACKUP | `gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only\gold_v2_13d2_tier2_manifest_match_rows.csv` | 19 |
| BACKUP | `gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only\gold_v2_13d2_tier2_manifest_mismatch_rows.csv` | 12 |

Expected selected artifacts: 5.
Expected total selected source rows: 104.
Expected PRIMARY source rows: 31.

## Field handling contract

Required dry-run candidate identity fields:

- `manifest_row_id`
- `component`
- `source_identity_type`
- `source_role`
- `source_row_number_1based`
- `source_key`
- `source_row_hash`
- `strategy_id`
- `source_status`

The ledger may also carry read-only auxiliary columns when present in the selected source CSV:

- `entry_time`
- `direction`
- `tp`
- `sl`
- `outcome`

`strategy_id`, `entry_time`, `direction`, `tp`, `sl`, and `outcome` must be read or derived only from existing selected CSV rows. 18K must not recalculate TP/SL from OHLC, must not infer outcome from price replay, and must not approximate missing values from memory or older logic.

## Output folder

`FX_OUTPUTS/gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only`

## Outputs

- `GOLD_V2_18K_TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY_REPORT.md`
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

## Required summary flags

On success:

- `audit_only`: true
- `dry_run_implemented`: true
- `dry_run_executed`: true
- `source_rows_read`: true
- `row_hash_computed`: true, scoped to dry-run candidate identity only
- `source_recovery_executed`: false
- `source_identity_finalized`: false
- `source_identity_recovered`: false
- `live_or_final_implementation_allowed`: false
- `oh_lc_replay_allowed`: false
- `live_enabled`: false
- `final_signal_allowed`: false
- `discord_send_allowed`: false
- `mt5_order_allowed`: false
- `ai_api_allowed`: false
- `live_hook_allowed`: false
- `no_signal_discord_notified`: false
- `ledger_is_source_of_truth`: false

## Audit method

18K must write these audits:

1. input existence audit for 18J and 18I inputs
2. implementation checks for upstream status, upstream STOP rows, upstream safety, selected artifact count, PRIMARY count, and required output fields
3. source artifact row-count audit comparing actual rows to 18J expected row counts
4. field derivation audit listing candidate columns, present columns, missing columns, and derivation status per artifact and field
5. dry-run validation checks confirming ledger row counts, required columns, false recovery/finalization flags, no AI API calls, no Discord/MT5/live hook calls, no NO_SIGNAL Discord notification, and no OHLC replay/reconstruction
6. safety matrix that keeps all final/live/external actions blocked

## Stop conditions

18K must stop with non-zero exit if any of these occur:

- required 18J/18I input is missing
- 18J status does not match the expected 18J success status
- 18J checks or 18J safety matrix contain any `STOP` row
- 18J already reports dry-run implementation, source row reads, or source recovery execution
- 18J planned artifact count is zero
- 18J PRIMARY artifact count is not exactly one
- a selected source CSV artifact is missing
- selected source CSV row counts do not match 18J expected row counts
- a required dry-run field recipe is missing
- all candidate columns for a required derived field are missing
- any ledger row has `source_recovery_executed`, `source_identity_finalized`, or `source_identity_recovered` true
- any live/final/external action would be enabled

## Success status

`TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

This status means only that the dry-run candidate identity ledger was generated for audit. It does not mean source recovery, source identity finalization, live evaluator readiness, final signal readiness, or source-of-truth acceptance.

## Required next gate

`18L_TIER2_SOURCE_IDENTITY_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY`

18L should validate that the 18K outputs load and remain safe. 18L must still not promote the dry-run candidate identity ledger to source-of-truth and must not enable live/final behavior.

## What was implemented in 18K

18K adds a Python script that creates an audit-only dry-run candidate identity ledger from 18J-selected CSV rows, using the corrected 18I field recipe. The implementation writes row-count, field-derivation, validation, blocker, next-gate, safety, summary, and report outputs.

The BAT launcher was attempted but blocked by the tool safety layer during GitHub write. Until the BAT is created manually, run the Python script directly from the repository root.

## Files to review

- this specification
- `scripts/gold_v2_runtime/audit_gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only.py`
- outputs under `FX_OUTPUTS/gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only`

## Execution order

1. Confirm 18I and 18J outputs already exist and are the latest audit-only outputs.
2. From the repository root, run `python scripts\gold_v2_runtime\audit_gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only.py`.
3. Review `gold_v2_18k_implementation_checks.csv`.
4. Review `gold_v2_18k_dry_run_validation_checks.csv`.
5. Review `gold_v2_18k_safety_matrix.csv`.
6. Review the report and summary JSON.

## Success conditions

- summary status equals the 18K success status
- implementation checks have zero `STOP` rows
- validation checks have zero `STOP` rows
- selected artifact actual row counts match 18J expected row counts
- candidate ledger row count equals actual selected source rows read
- source recovery/finalization/recovered flags remain false everywhere
- AI API, Discord, MT5, live hook, final signal, live evaluator, and NO_SIGNAL Discord notification remain disabled

## Outputs that must not be used yet

`gold_v2_18k_dry_run_candidate_identity_rows.csv` must not be treated as source-of-truth. It is only a dry-run candidate identity ledger pending later audit gates.
