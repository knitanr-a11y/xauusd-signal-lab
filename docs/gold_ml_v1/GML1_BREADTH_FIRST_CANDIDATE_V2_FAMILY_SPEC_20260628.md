# GML1 Breadth-First Candidate V2 Family Specification

Date: 2026-06-28  
Mode: audit-only  
Entry source: M5 closed bars  
Context: closed M15/H1/H4/D1 bars only

This specification is frozen before raw-proposal density and before labels or outcomes are inspected.

## Shared calculations

- M5/M15/H1/H4 ATR14: Wilder ATR.
- EMA20, EMA50 and EMA200: exponential moving average with `adjust=False`.
- Donchian levels: prior high/low using `shift(1)` before rolling maximum/minimum.
- Bollinger bands: 20-bar population standard deviation, two standard deviations.
- Bollinger-width and ATR percentiles: current value compared with the previous 256 completed M5 values; the current value is excluded from the reference distribution.
- Close location: `(close-low)/(high-low)`.
- Body, range, wick and distance tests are normalized by current M5 ATR14 unless explicitly stated otherwise.
- LONG/SHORT rules are exact mirrors unless the text explicitly states otherwise.
- Direct conditions emit only on false-to-true onset, preventing repeated proposals from an unchanged state.
- Each state-machine candidate ID may hold one pending setup. Expiry is checked before invalidation, and invalidation before confirmation.

## Higher-timeframe contexts

Continuation LONG:

- H1 EMA20 > EMA50;
- H4 `(EMA20-EMA50)/ATR14 >= -0.10`.

Continuation SHORT is the mirror.

Permissive reversal LONG:

- H1 `(EMA20-EMA50)/ATR14 >= -0.50`.

Permissive reversal SHORT is the mirror.

## Families

### BF01 — M5 EMA20 reclaim continuation

IDs: `GML1-BF2-01-L`, `GML1-BF2-01-S`

LONG:

- continuation LONG context;
- previous close is at or below previous EMA20;
- current low is at or below `EMA20 + 0.10 ATR`;
- current close is at or above `EMA20 + 0.10 ATR`;
- signed body is at least `0.20 ATR`;
- close location is at least 0.60.

### BF02 — M5 EMA20/EMA50 band recovery

IDs: `GML1-BF2-02-L`, `GML1-BF2-02-S`

LONG:

- EMA20 > EMA50;
- last closed M15 EMA20 > EMA50;
- H1 gap is not below `-0.10 ATR`;
- at least one of the previous three M5 closes was at or below the EMA-band upper edge;
- current close is at least `0.10 ATR` above the upper edge;
- signed body is at least `0.25 ATR`;
- close location is at least 0.65.

### BF03 — M5 Donchian-20 breakout onset

IDs: `GML1-BF2-03-L`, `GML1-BF2-03-S`

LONG:

- continuation LONG context;
- current close exceeds prior 20-bar high by `0.10 ATR`;
- signed body is at least `0.30 ATR`;
- close location is at least 0.65.

### BF04 — M5 Donchian-20 breakout retest

IDs: `GML1-BF2-04-L`, `GML1-BF2-04-S`

Setup is BF03. Freeze the prior 20-bar level. During the next six M5 bars:

- invalidate on a close more than `0.20 ATR` back through the level;
- confirm on the first touch of the level or `0.10 ATR` beyond it that closes at least `0.03 ATR` back in the breakout direction with a correctly signed body.

### BF05 — M5 Donchian-50 breakout acceptance

IDs: `GML1-BF2-05-L`, `GML1-BF2-05-S`

Setup LONG:

- continuation LONG context;
- current close exceeds prior 50-bar high by `0.05 ATR`;
- signed body is at least `0.25 ATR`.

Freeze the level. During the next three bars, confirm on the first close at least `0.05 ATR` beyond the level while no close has crossed `0.15 ATR` back through it.

### BF06 — M5 compression release

IDs: `GML1-BF2-06-L`, `GML1-BF2-06-S`

LONG:

- continuation LONG context;
- lagged Bollinger-width percentile is at or below 0.20;
- close is above the Bollinger upper band and prior 20-bar high;
- range is at least `1.20 ATR`;
- signed body is positive;
- close location is at least 0.70.

### BF07 — Compression-release first pullback

IDs: `GML1-BF2-07-L`, `GML1-BF2-07-S`

Setup is BF06. Freeze the release level and EMA20 at setup. Ignore the first later bar. During bars two through eight:

- invalidate on a close `0.25 ATR` through the release level;
- confirm when price touches current EMA20 within `0.15 ATR`, remains beyond the release level, and closes in the breakout direction with close location at least 0.60 for LONG or at most 0.40 for SHORT.

### BF08 — Inside-bar continuation breakout

IDs: `GML1-BF2-08-L`, `GML1-BF2-08-S`

LONG:

- continuation LONG context;
- bar `t-1` is inside bar `t-2`;
- parent bar range is at least `1.00 ATR(t-2)`;
- parent signed body is positive;
- current close exceeds the inside-bar high by `0.05 ATR`;
- current signed body is positive.

### BF09 — Impulse, shallow pause, continuation

IDs: `GML1-BF2-09-L`, `GML1-BF2-09-S`

LONG three-bar pattern:

- continuation LONG context;
- bar `t-2` body is at least `0.80 ATR(t-2)` and close location at least 0.75;
- bar `t-1` range is at most `0.70 ATR(t-1)`, remains in the upper 60% of the impulse range and does not close below the impulse midpoint;
- current close exceeds the pause-bar high by `0.05 ATR` with positive body.

### BF10 — Closed-M15 impulse with M5 micro pullback

IDs: `GML1-BF2-10-L`, `GML1-BF2-10-S`

LONG:

- last closed M15 bar ended no more than 15 minutes before the M5 decision;
- M15 signed body is at least `0.80 M15 ATR` and close location at least 0.75;
- continuation LONG context;
- current M5 low touches M5 EMA20 within `0.15 ATR`;
- current close is above EMA20 with positive body and close location at least 0.60.

### BF11 — Closed-M15 Donchian breakout with M5 retest

IDs: `GML1-BF2-11-L`, `GML1-BF2-11-S`

LONG:

- last closed M15 bar ended no more than 30 minutes before the M5 decision;
- that M15 close exceeded its prior 20-bar high by at least `0.05 M15 ATR`;
- continuation LONG context;
- current M5 trades at or below `frozen M15 breakout level + 0.10 M5 ATR`;
- current close is at least `0.03 M5 ATR` above the frozen level with positive body.

### BF12 — Failed M5 Donchian-20 break recovery

IDs: `GML1-BF2-12-L`, `GML1-BF2-12-S`

LONG:

- permissive reversal LONG context;
- low trades below prior 20-bar low by `0.10 ATR`;
- the same bar closes back above the prior low;
- lower wick is at least 35% of range;
- close location is at least 0.65.

### BF13 — Failed M5 Donchian-50 break recovery

IDs: `GML1-BF2-13-L`, `GML1-BF2-13-S`

Same as BF12 using the prior 50-bar level and a minimum wick fraction of 0.40.

### BF14 — Previous closed-day high/low sweep recovery

IDs: `GML1-BF2-14-L`, `GML1-BF2-14-S`

LONG:

- permissive reversal LONG context;
- current low trades below the last closed D1 low by `0.05 ATR`;
- current close finishes back above that D1 low;
- lower wick is at least 35% of range;
- close location is at least 0.65.

### BF15 — Previous closed-day breakout acceptance

IDs: `GML1-BF2-15-L`, `GML1-BF2-15-S`

LONG:

- continuation LONG context;
- previous M5 close was not above the last closed D1 high;
- current close exceeds that high by `0.10 ATR`;
- signed body is at least `0.30 ATR`;
- close location is at least 0.70.

### BF16 — Previous closed-day breakout retest

IDs: `GML1-BF2-16-L`, `GML1-BF2-16-S`

Setup is BF15. Freeze the last closed D1 level. During the next twelve M5 bars:

- invalidate on a close `0.20 ATR` back through the level;
- confirm on the first level touch that closes `0.03 ATR` beyond it in the breakout direction with correctly signed body.

### BF17 — Closed-H1 range boundary rejection

IDs: `GML1-BF2-17-L`, `GML1-BF2-17-S`

LONG:

- permissive reversal LONG context;
- current low trades below the prior closed-H1 20-bar low by `0.05 M5 ATR`;
- current close finishes back above the H1 level;
- lower wick is at least 40% of range;
- close location is at least 0.65.

### BF18 — High-volatility exhaustion recovery

IDs: `GML1-BF2-18-L`, `GML1-BF2-18-S`

LONG:

- permissive reversal LONG context;
- lagged M5 ATR percentile is at least 0.80;
- current range is at least `1.50 ATR`;
- four-bar price displacement is at most `-1.00 ATR`;
- lower wick is at least 45% of range;
- close location is at least 0.65.

## Raw proposal requirements

Every row must preserve candidate ID, direction, decision time, M5 source-bar open and close, exact-M1 availability, label-free strength, M5/M15/H1/H4/D1 context timestamps, volatility and trend regimes, and all setup/confirmation levels required to reproduce the event.

No deduplication, one-position handling, label, TP/SL result, R value or model score may alter the raw registry.
