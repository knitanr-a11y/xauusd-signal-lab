# GML1 M1 Microstructure V5 Compute Addendum

Date: 2026-06-28  
Mode: audit-only

The direct implementation of every rolling median and percentile on 1.22 million M1 rows exceeded the bounded audit execution window before any candidate or outcome result was produced.

The following causally equivalent two-stage implementation is frozen before results:

1. Build an exact M1-to-M5 block for each completed five-minute interval. A block is valid only when it contains the expected five consecutive M1 bars.
2. Calculate exact within-block M1 statistics: returns, realized variance, directional efficiency, spread median/maximum/90th percentile, tick-volume burst and concentration, wick shares, close location, sweep/reclaim counts and stagnation.
3. Build 15-, 30- and 60-minute features from the previous 3, 6 and 12 valid five-minute blocks. Additive statistics are summed; rates and shares are weighted or averaged; maxima and burst measures use the maximum; spread and volume percentile proxies use the maximum of the constituent exact five-minute block percentiles.
4. A higher-window feature is invalid when the constituent five-minute decisions are not exactly consecutive.

No label, WR, PF, R, 2025 result or 2026 result was inspected before this implementation was frozen. Event definitions, chronology, candidate gates and model gates remain unchanged.
