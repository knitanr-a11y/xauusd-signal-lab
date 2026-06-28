# GML1 New Independent Candidate Discovery V1 — Candidate Family Specification

Date: 2026-06-28  
Mode: audit-only  
Stage: `GML1_NEW_INDEPENDENT_CANDIDATE_DISCOVERY_V1_AUDIT_ONLY`

This specification is frozen before any new-candidate label, TP/SL result, exit result, WR, PF, R, drawdown or monthly profitability is inspected.

## 1. Prospective-use rule

- Candidate definitions and all numeric constants below are frozen without using 2026 outcomes.
- 2026 is replayed prospectively in timestamp order.
- At each 2026 decision time, only the current closed source bar and earlier closed bars may be used.
- CSV `time` is MT5 server naive bar-open time.
- M15 decision time is `time + 15 minutes`.
- Exact M1 bar-open at decision time is mandatory.
- No next-M1 fallback is allowed.
- H1/H4/D1 context must have source bar-close time less than or equal to decision time.
- The latest valid CSV row is closed by contract.

## 2. Shared causal calculations

All calculations use completed bars only.

- M15 ATR14: Wilder ATR.
- M15 EMA20 and EMA50: standard exponential moving averages with `adjust=False`.
- H1 EMA20 and EMA50: same definition.
- H4 EMA20 and EMA50: same definition.
- Previous-high/low levels use `shift(1)` before the rolling maximum/minimum.
- Bollinger basis uses M15 rolling mean 20 and population standard deviation 20.
- Bollinger width is `(upper - lower) / ATR14`.
- Bollinger-width percentile is the percentile rank of the prior completed width inside the previous 256 completed M15 widths. The current decision bar is excluded from the reference distribution.
- All distances are ATR-normalized using the ATR available on the current closed decision bar.
- No future-confirmed ZigZag, centered window, interpolation, backward fill or future bar is allowed.

## 3. Common higher-timeframe context

For continuation families:

- LONG context: H1 EMA20 is above H1 EMA50 and H4 EMA20-EMA50 gap is not below `-0.10 * H4 ATR14`.
- SHORT context: H1 EMA20 is below H1 EMA50 and H4 EMA20-EMA50 gap is not above `+0.10 * H4 ATR14`.

For failed-break recovery:

- LONG context: H1 EMA20-EMA50 gap is at least `-0.15 * H1 ATR14`.
- SHORT context: H1 EMA20-EMA50 gap is at most `+0.15 * H1 ATR14`.

These are symmetric directional definitions. No 2026 density or outcome is used to select them.

## 4. Candidate families

Each direction has a separate immutable candidate ID. A proposal is emitted once per completed state-machine setup. Raw proposals are saved before deduplication, one-position handling, conflict arbitration or outcome filtering.

### NCD-001 — Frozen 20-bar breakout-level retest continuation

Candidate IDs:

- `GML1-NCD-001-L`
- `GML1-NCD-001-S`

LONG setup:

1. On breakout bar `b`, `close[b] > previous_high_20[b] + 0.10 * ATR14[b]`.
2. `signed_body[b] >= 0.35 * ATR14[b]`.
3. LONG higher-timeframe context is true at `b`.
4. Freeze `previous_high_20[b]` as the breakout level.
5. During bars `b+1` through `b+8`, invalidate if any close is below `level - 0.20 * ATR14[current]`.
6. Emit on the first bar whose low is at or below `level + 0.15 * ATR14[current]`, close is at or above `level + 0.05 * ATR14[current]`, and signed body is positive.

SHORT is the exact mirror using previous low, negative body and reversed inequalities.

### NCD-002 — Frozen 50-bar Donchian shallow reclaim

Candidate IDs:

- `GML1-NCD-002-L`
- `GML1-NCD-002-S`

LONG setup:

1. On breakout bar `b`, `close[b] > previous_high_50[b] + 0.05 * ATR14[b]`.
2. `signed_body[b] >= 0.25 * ATR14[b]`.
3. LONG higher-timeframe context is true.
4. Freeze `previous_high_50[b]` as the Donchian level.
5. Search bars `b+1` through `b+6`.
6. Emit on the first bar that trades at or below the frozen level, does not trade below `level - 0.40 * ATR14[current]`, and closes back above `level + 0.03 * ATR14[current]` with positive signed body.
7. Invalidate on a close below `level - 0.20 * ATR14[current]`.

SHORT is the exact mirror.

### NCD-003 — Compression release followed by first EMA20 pullback

Candidate IDs:

- `GML1-NCD-003-L`
- `GML1-NCD-003-S`

LONG setup:

1. Before breakout bar `b`, lagged Bollinger-width percentile is at or below `0.25`.
2. `close[b] > previous_high_20[b]` and `close[b] > Bollinger upper[b]`.
3. `range[b] >= 1.00 * ATR14[b]` and signed body is positive.
4. LONG higher-timeframe context is true.
5. Freeze `previous_high_20[b]` as the release level.
6. Ignore `b+1`; search `b+2` through `b+12` for the first pullback.
7. Emit when low is at or below `EMA20[current] + 0.20 * ATR14[current]`, close remains above the release level, close location in the bar is at least `0.60`, and signed body is positive.
8. Invalidate on a close below `release_level - 0.25 * ATR14[current]`.

SHORT is the exact mirror using Bollinger lower, previous low and close location at most `0.40`.

### NCD-004 — EMA20/EMA50 band recovery continuation onset

Candidate IDs:

- `GML1-NCD-004-L`
- `GML1-NCD-004-S`

LONG event:

1. M15 EMA20 is above M15 EMA50.
2. LONG higher-timeframe context is true.
3. At least one of the prior four completed M15 closes is at or below the upper edge of the EMA20/EMA50 band.
4. Current close is above the upper band edge by at least `0.10 * ATR14`.
5. Current signed body is at least `0.25 * ATR14`.
6. Current close location is at least `0.65`.
7. Emit only on the inactive-to-active onset; consecutive active bars do not create repeated raw proposals.

SHORT is the exact mirror.

### NCD-005 — Failed 20-bar break followed by structure recovery

Candidate IDs:

- `GML1-NCD-005-L`
- `GML1-NCD-005-S`

LONG setup:

1. On failure bar `f`, low trades below `previous_low_20[f] - 0.10 * ATR14[f]`.
2. The same closed bar finishes back above `previous_low_20[f]`.
3. Freeze the failure-bar high and the previous-low level.
4. LONG failed-break context is true.
5. During bars `f+1` through `f+4`, invalidate if a close is below `frozen_previous_low - 0.20 * ATR14[current]`.
6. Emit on the first bar that closes above the failure-bar high with positive signed body and close location at least `0.60`.

SHORT is the exact mirror: failed break above the previous 20-bar high, close back below it, then confirmation below the failure-bar low.

## 5. Raw proposal strength

`proposal_strength_label_free` is diagnostic only and must not change whether a proposal exists.

- NCD-001: confirmation close distance beyond frozen level divided by ATR.
- NCD-002: reclaim close distance beyond frozen level divided by ATR.
- NCD-003: release-bar range/ATR plus confirmation close-location advantage.
- NCD-004: close distance beyond the EMA band divided by ATR.
- NCD-005: confirmation close distance beyond the failure-bar opposite extreme divided by ATR.

No label or future outcome enters proposal strength.

## 6. 2026 live-like replay

- Definitions are not changed after viewing any 2026 proposal count or result.
- The generator must support a prefix-only run ending at any M15 bar.
- Proposals with decision time in 2026 must be identical between a prefix run ending at that point and a later full-history run.
- State is updated only when each closed source bar arrives.
- Exact M1 availability is checked at each decision time.
- A proposal may be recorded as raw structural detection even when exact M1 is absent, but `entry_eligible` must be false and no label or trade simulation may use a later M1 row.

## 7. Label-free audit only

Before any ML-03 label join, report:

- raw proposal count by candidate, direction, year and month;
- LONG/SHORT ratio;
- MT5 server-hour and weekday distribution;
- volatility/trend/range regime distribution;
- same-decision overlap with A_CORE, B_STATE, P18 and W024A;
- holding-interval overlap with the four-sleeve benchmark using only already-frozen benchmark intervals;
- within-family and cross-family duplicate decision times;
- exact-M1 availability;
- 2026 prefix replay parity.

No WR, PF, R, TP/SL, exit result or unresolved horizon result may be inspected in this stage.

## 8. Machine-learning policy

Machine learning is allowed only after this candidate specification, generator, raw proposal registry and label-free audit are hash-frozen.

Any later ML evaluation must:

- train only on chronologically earlier resolved proposals;
- use expanding purged walk-forward splits;
- treat 2026 as prospective out-of-sample replay;
- never add an open proposal result to training or health history;
- persist the model, pipeline/scaler, exact feature order, calibration, numeric threshold, split manifest and all proposal scores;
- remain audit-only unless separately authorized.

## 9. Controls

- `audit_only = true`
- `live_ready = false`
- `final_signal = false`
- `discord = false`
- `mt5_order = false`
- no automatic retraining, promotion or registration
- current four-sleeve live runtime is not modified
