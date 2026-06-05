# GOLD V2 17F MEDIUM full-set candidate mapping plan audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17F_MEDIUM_FULL_SET_CANDIDATE_MAPPING_PLAN_AUDIT_ONLY`
Mode: audit-only

## Purpose

17F writes a MEDIUM full-set candidate mapping plan after 17E consolidation succeeded.

This is a planning gate only. It does not generate executable live rules and does not connect MEDIUM to final signal, Discord, MT5, AI API, or live hooks.

## Source of truth

Use audited outputs only:

1. `FX_OUTPUTS/gold_v2_17e_medium_full_set_post_17c_17d_consolidation_audit_only/gold_v2_17e_medium_full_set_consolidation_summary.json`
2. `FX_OUTPUTS/gold_v2_17e_medium_full_set_post_17c_17d_consolidation_audit_only/gold_v2_17e_component_status_matrix.csv`
3. `FX_OUTPUTS/gold_v2_17e_medium_full_set_post_17c_17d_consolidation_audit_only/gold_v2_17e_readiness_checks.csv`
4. `FX_OUTPUTS/gold_v2_17e_medium_full_set_post_17c_17d_consolidation_audit_only/gold_v2_17e_safety_matrix.csv`
5. `FX_OUTPUTS/gold_v2_17c_range96_refined_reconciliation_audit_only/gold_v2_17c_range96_candidate_source_freeze_preview.json`
6. `FX_OUTPUTS/gold_v2_17d_vol_trmean32_refined_reconciliation_audit_only/gold_v2_17d_vol_trmean32_candidate_source_freeze_preview.json`

Do not use OHLC. Do not rediscover candidates. Do not approximate RANGE96 or VOL_TRMEAN32 conditions.

## Expected input state

17E must have status:

`MEDIUM_FULL_SET_POST_17C_17D_CONSOLIDATED_AUDIT_ONLY_LIVE_BLOCKED`

17C and 17D freeze previews must have candidate status:

`SOURCE_ROW_FREEZE_PREVIEW_WRITTEN_NOT_EXECUTABLE_RULE_NOT_LIVE`

Expected preview counts:

- RANGE96_REFINED: rule 51 / combined 117
- VOL_TRMEAN32_REFINED: rule 36 / combined 104

## Output folder

`FX_OUTPUTS/gold_v2_17f_medium_full_set_candidate_mapping_plan_audit_only`

## Main outputs

- `GOLD_V2_17F_MEDIUM_FULL_SET_CANDIDATE_MAPPING_PLAN_AUDIT_ONLY_REPORT.md`
- `gold_v2_17f_medium_full_set_candidate_mapping_plan_summary.json`
- `gold_v2_17f_input_audit.csv`
- `gold_v2_17f_candidate_mapping_plan.csv`
- `gold_v2_17f_required_next_gates.csv`
- `gold_v2_17f_blockers.csv`
- `gold_v2_17f_safety_matrix.csv`

## Planned component handling

- `TIER2_HVT`: use the already audited 13L candidate mapping/load-smoke chain as an existing candidate source. Do not rederive from OHLC.
- `RANGE96_REFINED`: use 17C source-row identity freeze preview as a candidate input. It still requires a later audit-only candidate mapping/load-smoke/dry-run gate.
- `VOL_TRMEAN32_REFINED`: use 17D source-row identity freeze preview as a candidate input. It still requires a later audit-only candidate mapping/load-smoke/dry-run gate.

## Success status

`MEDIUM_FULL_SET_CANDIDATE_MAPPING_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED`

This means the plan is ready, not that live execution is allowed.

## Stop conditions

Stop if:

- any required input is missing,
- 17E status is not the expected success status,
- 17E readiness or safety contains STOP,
- 17C/17D freeze preview statuses or counts do not match expectations,
- any external action flag is true.

## Safety

All external actions remain false:

- final signal
- Discord
- MT5
- AI API
- live hook
- NO_SIGNAL Discord notification
