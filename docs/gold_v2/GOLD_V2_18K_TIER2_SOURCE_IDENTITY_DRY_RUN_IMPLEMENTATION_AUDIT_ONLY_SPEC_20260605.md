# GOLD V2 18K TIER2 source identity dry-run implementation audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18K_TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY`
Mode: audit-only

## Purpose

18K implements and executes a dry-run row-level source identity extraction using the 18J implementation plan and the corrected 18I field recipe.

This is still not source recovery finalization. All outputs must be marked dry-run only. The generated row-level identity rows are diagnostic artifacts only and must not be used as source-of-truth until a later review gate accepts them.

## Allowed actions

18K may:

- read the 18J plan outputs
- read the 18I dry-run field recipe
- read the selected candidate source CSV artifacts listed by 18J
- create dry-run row-level identity rows
- compute dry-run row hashes for audit comparison
- write audit-only CSV/JSON/MD outputs

## Forbidden actions

18K must not:

- mark source identity as final
- update rule manifests
- implement predicates or arbitration
- replay OHLC
- reconstruct from OHLC
- enable live/final signal paths
- send Discord notifications
- place MT5 orders
- call AI APIs
- call live hooks
- notify Discord on NO_SIGNAL

## Inputs

Use these 18J outputs:

- `gold_v2_18j_tier2_source_identity_dry_run_implementation_plan_summary.json`
- `gold_v2_18j_plan_checks.csv`
- `gold_v2_18j_planned_artifacts.csv`
- `gold_v2_18j_planned_output_contract.csv`
- `gold_v2_18j_planned_stop_conditions.csv`
- `gold_v2_18j_required_next_gates.csv`
- `gold_v2_18j_blockers.csv`
- `gold_v2_18j_safety_matrix.csv`

Also use the corrected 18I recipe:

- `gold_v2_18i_dry_run_field_recipe.csv`

## Output folder

`FX_OUTPUTS/gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only`

## Outputs

- `GOLD_V2_18K_TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY_REPORT.md`
- `gold_v2_18k_tier2_source_identity_dry_run_implementation_summary.json`
- `gold_v2_18k_input_audit.csv`
- `gold_v2_18k_implementation_checks.csv`
- `gold_v2_18k_dry_run_identity_rows.csv`
- `gold_v2_18k_artifact_row_counts.csv`
- `gold_v2_18k_field_derivation_audit.csv`
- `gold_v2_18k_required_next_gates.csv`
- `gold_v2_18k_blockers.csv`
- `gold_v2_18k_safety_matrix.csv`

## Success status

`TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTED_AUDIT_ONLY_SOURCE_RECOVERY_BLOCKED`

## Required next gate

`18L_TIER2_SOURCE_IDENTITY_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY`

18L should validate that the dry-run outputs are readable and internally consistent. It must still not promote the dry-run identities to source-of-truth.
