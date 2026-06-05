# GOLD V2 18H TIER2 row-level source identity extraction plan audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18H_TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_PLAN_AUDIT_ONLY`
Mode: audit-only

## Purpose

18H uses the 18G read-only structural inspection outputs to plan how a later step could extract TIER2 row-level source identity.

18H is planning only. It must not recover the identity, must not choose final source rows, must not hash source rows, must not reconstruct from OHLC, must not implement predicates or arbitration, must not replay OHLC, must not enable live/final paths, and must not enable external actions.

## Inputs

Use only these 18G outputs:

- `gold_v2_18g_tier2_source_artifact_content_inspection_execution_summary.json`
- `gold_v2_18g_content_inspection_checks.csv`
- `gold_v2_18g_inspected_artifact_results.csv`
- `gold_v2_18g_required_identity_field_presence.csv`
- `gold_v2_18g_required_next_gates.csv`
- `gold_v2_18g_blockers.csv`
- `gold_v2_18g_safety_matrix.csv`

## Required fields carried from 18B

- `manifest_row_id`
- `component`
- `source_identity_type`
- `source_role`
- `source_row_number_1based`
- `source_key`
- `source_row_hash`
- `strategy_id`
- `source_status`

## Output folder

`FX_OUTPUTS/gold_v2_18h_tier2_source_identity_extraction_plan_audit_only`

## Outputs

- `GOLD_V2_18H_TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_PLAN_AUDIT_ONLY_REPORT.md`
- `gold_v2_18h_tier2_source_identity_extraction_plan_summary.json`
- `gold_v2_18h_input_audit.csv`
- `gold_v2_18h_plan_checks.csv`
- `gold_v2_18h_identity_field_mapping_plan.csv`
- `gold_v2_18h_candidate_artifact_ranking.csv`
- `gold_v2_18h_missing_required_fields.csv`
- `gold_v2_18h_required_next_gates.csv`
- `gold_v2_18h_blockers.csv`
- `gold_v2_18h_safety_matrix.csv`

## Success status

`TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_BLOCKED`

This means the extraction plan is ready. It does not mean the source identity has been extracted or recovered.

## Recommended next step after success

`18I_TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_DRY_RUN_DESIGN_AUDIT_ONLY`

18I must still be design/dry-run planning only unless explicit approval is separately provided.
