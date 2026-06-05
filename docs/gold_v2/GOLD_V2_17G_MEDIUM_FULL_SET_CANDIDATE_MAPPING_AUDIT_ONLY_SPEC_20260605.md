# GOLD V2 17G MEDIUM full-set candidate mapping audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17G_MEDIUM_FULL_SET_CANDIDATE_MAPPING_AUDIT_ONLY`
Mode: audit-only

## Purpose

17G materializes the 17F MEDIUM full-set candidate mapping plan into an audit-only candidate manifest.

The manifest maps only audited source identities:

- `TIER2_HVT` from the existing 13L candidate mapping/load-smoke summary chain reference
- `RANGE96_REFINED` from the 17C source-row identity freeze index
- `VOL_TRMEAN32_REFINED` from the 17D source-row identity freeze index

17G does not create executable live rules and does not connect MEDIUM to final signal, Discord, MT5, AI API, or live hooks.

## Source of truth

Use audited artifacts only:

1. `FX_OUTPUTS/gold_v2_17f_medium_full_set_candidate_mapping_plan_audit_only/gold_v2_17f_medium_full_set_candidate_mapping_plan_summary.json`
2. `FX_OUTPUTS/gold_v2_17f_medium_full_set_candidate_mapping_plan_audit_only/gold_v2_17f_candidate_mapping_plan.csv`
3. `FX_OUTPUTS/gold_v2_17f_medium_full_set_candidate_mapping_plan_audit_only/gold_v2_17f_required_next_gates.csv`
4. `FX_OUTPUTS/gold_v2_17f_medium_full_set_candidate_mapping_plan_audit_only/gold_v2_17f_safety_matrix.csv`
5. `FX_OUTPUTS/gold_v2_13l_medium_tier2_hvt_candidate_mapping_load_smoke_audit/gold_v2_13l_load_smoke_summary.json`
6. `FX_OUTPUTS/gold_v2_17c_range96_refined_reconciliation_audit_only/gold_v2_17c_range96_candidate_source_freeze_index.csv`
7. `FX_OUTPUTS/gold_v2_17c_range96_refined_reconciliation_audit_only/gold_v2_17c_range96_candidate_source_freeze_preview.json`
8. `FX_OUTPUTS/gold_v2_17d_vol_trmean32_refined_reconciliation_audit_only/gold_v2_17d_vol_trmean32_candidate_source_freeze_index.csv`
9. `FX_OUTPUTS/gold_v2_17d_vol_trmean32_refined_reconciliation_audit_only/gold_v2_17d_vol_trmean32_candidate_source_freeze_preview.json`

Do not use OHLC. Do not rediscover candidates. Do not infer RANGE96/VOL rule predicates.

## Important TIER2 handling

17G does not reconstruct TIER2_HVT rows from OHLC. If an audited 13L row-level manifest is not available, 17G records TIER2_HVT as a single `13L_SUMMARY_CHAIN_REFERENCE` row. This preserves the existing audited 13L chain without inventing row identities.

A later step may expand TIER2_HVT only if an audited 13L row-level source identity artifact is explicitly available.

## Expected state

17F must have status:

`MEDIUM_FULL_SET_CANDIDATE_MAPPING_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED`

17C freeze preview must show:

- `RANGE96_REFINED` rule rows 51
- `RANGE96_REFINED` combined rows 117
- candidate status `SOURCE_ROW_FREEZE_PREVIEW_WRITTEN_NOT_EXECUTABLE_RULE_NOT_LIVE`

17D freeze preview must show:

- `VOL_TRMEAN32_REFINED` rule rows 36
- `VOL_TRMEAN32_REFINED` combined rows 104
- candidate status `SOURCE_ROW_FREEZE_PREVIEW_WRITTEN_NOT_EXECUTABLE_RULE_NOT_LIVE`

17G expected manifest minimum:

- 1 TIER2_HVT summary-chain reference row
- 168 RANGE96 source identity rows from the 17C freeze index
- 140 VOL_TRMEAN32 source identity rows from the 17D freeze index

## Output folder

`FX_OUTPUTS/gold_v2_17g_medium_full_set_candidate_mapping_audit_only`

## Main outputs

- `GOLD_V2_17G_MEDIUM_FULL_SET_CANDIDATE_MAPPING_AUDIT_ONLY_REPORT.md`
- `gold_v2_17g_medium_full_set_candidate_mapping_summary.json`
- `gold_v2_17g_input_audit.csv`
- `gold_v2_17g_full_set_candidate_manifest.csv`
- `gold_v2_17g_component_counts.csv`
- `gold_v2_17g_mapping_checks.csv`
- `gold_v2_17g_blockers.csv`
- `gold_v2_17g_safety_matrix.csv`

## Success status

`MEDIUM_FULL_SET_CANDIDATE_MAPPING_READY_AUDIT_ONLY_LIVE_BLOCKED`

This means an audit-only manifest exists. It does not mean live execution is allowed.

## Stop conditions

Stop if:

- any required artifact is missing,
- 17F status is not successful,
- 17F safety contains STOP,
- 17C or 17D freeze preview status/counts do not match expectations,
- 17C/17D freeze index source row counts do not match expected totals,
- any external action flag is true.

## Safety

All external actions remain false:

- final signal
- Discord
- MT5
- AI API
- live hook
- NO_SIGNAL Discord notification
