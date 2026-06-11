# GOLD V3 Stage104 — High-Vol Polarity and Proxy Audit-Only Spec

Created JST: `2026-06-11`

Stage name:

`GOLD_V3_104_HIGH_VOL_POLARITY_AND_PROXY_AUDIT_ONLY`

READY status:

`GOLD_V3_104_HIGH_VOL_POLARITY_AND_PROXY_READY_AUDIT_ONLY`

## Purpose

Stage103 showed high-volatility rows exist, but current high-vol siblings can still be reachable when `high_vol_source_rows_for_ranks` is zero.

This indicates a likely polarity bug: Stage45 uses `cat()` as an exclusion filter, and high-vol siblings append `cat("HV_ROLLING_Q70", "is_high_vol", True)`. Therefore the current high-vol sibling may exclude `is_high_vol=True` rows instead of requiring them.

Stage104 verifies this without changing runtime behavior by comparing:

- current Stage45 high-vol sibling semantics,
- intended inherited high-vol semantics: base source + base filters + require `is_high_vol == True`,
- independent high-vol universe: `is_high_vol == True` before inherited source filters.

## Safety

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, final signal, source CSV mutation, candidate pool mutation, or manual candidate demotion/removal.
