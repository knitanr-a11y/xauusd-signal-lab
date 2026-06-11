# GOLD V3 Stage103 — High-Vol Reachability Audit-Only Spec

Created JST: `2026-06-11`

Stage name:

`GOLD_V3_103_HIGH_VOL_REACHABILITY_AUDIT_ONLY`

READY status:

`GOLD_V3_103_HIGH_VOL_REACHABILITY_READY_AUDIT_ONLY`

## Purpose

Investigate why high-volatility siblings are not producing live closed-candle signals.

Current GOLD V3 high-vol candidates are not independent entry rules. They are Stage45 high-vol siblings created by copying each base candidate's filters and appending `is_high_vol=True`.

Stage103 measures, for the post-last-detection window:

- total M15 rows,
- high-vol M15 rows,
- R1/R2 source rows,
- R1/R2 source rows that are high-vol,
- base candidate rows after original filters,
- high-vol sibling rows after original filters plus `is_high_vol=True`,
- high-vol rows blocked by inherited R1/R2 source conditions.

## Safety

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, final signal, source CSV mutation, candidate pool mutation, or manual candidate demotion/removal.
