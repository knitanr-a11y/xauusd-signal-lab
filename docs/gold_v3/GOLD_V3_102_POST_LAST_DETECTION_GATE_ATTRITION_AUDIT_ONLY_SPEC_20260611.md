# GOLD V3 Stage102 — Post Last Detection Gate Attrition Audit-Only Spec

Created JST: `2026-06-11`

Stage name:

`GOLD_V3_102_POST_LAST_DETECTION_GATE_ATTRITION_AUDIT_ONLY`

READY status:

`GOLD_V3_102_POST_LAST_DETECTION_GATE_ATTRITION_READY_AUDIT_ONLY`

## Purpose

Investigate why Stage69 produced zero latest condition candidates for the Stage99 128-bar replay window, even though historical Stage69 detection is active.

Stage101 showed the last detected condition time was `2026-06-02 15:00`, while the Stage99 128-bar replay window started around `2026-06-09 20:30`.

Stage102 decomposes the post-last-detection interval into:

1. R1/R2 source-row availability,
2. candidate-level final pass counts,
3. per-filter rejection and sequential attrition,
4. recent feature ranges for `h4_ret4`, `m15_atr28`, rolling q70, high-vol flag, JST hour, and weekday.

## Inputs

- live CSVs: `goldsharp_m15.csv`, `goldsharp_m5.csv`, `goldsharp_h4.csv`
- Stage50 q70 state
- Stage68 summary
- Stage99 replay results
- Stage45 audited candidate/filter functions

## Outputs

Folder:

`FX_OUTPUTS/gold_v3/102c/`

Files:

- `paste_me.txt`
- `summary.json`
- `source_rank_daily_counts.csv`
- `candidate_gate_attrition.csv`
- `filter_reject_counts.csv`
- `filter_sequential_attrition.csv`
- `recent_feature_summary.csv`
- `validation.csv`
- `blockers.csv`
- `report.md`

## Safety

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, final signal, source CSV mutation, candidate pool mutation, or manual candidate demotion/removal.
