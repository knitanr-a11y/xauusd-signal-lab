# GML1 Breadth-First Candidate V2B Density Addendum

Date: 2026-06-28  
Mode: audit-only

The first V2 raw-density replay was completed without labels or outcomes. Thirteen directional candidates had fewer than 200 raw proposals across 2024–2025. The original V2 IDs and definitions remain immutable. The following separately identified V2B variants are added before any label join.

## BF2B-06 — Broader compression release

IDs: `GML1-BF2B-06-L`, `GML1-BF2B-06-S`

Changes from BF06 only:

- lagged Bollinger-width percentile threshold: 0.30 instead of 0.20;
- minimum range: `1.00 ATR` instead of `1.20 ATR`;
- close-location threshold: 0.65/0.35 instead of 0.70/0.30.

All breakout-level and higher-timeframe requirements remain unchanged.

## BF2B-07 — Broader first pullback after BF2B-06

IDs: `GML1-BF2B-07-L`, `GML1-BF2B-07-S`

- setup is BF2B-06;
- search bars two through twelve;
- EMA20 touch tolerance is `0.25 ATR`;
- confirmation close may be no more than `0.05 ATR` back through the frozen release level;
- invalidation is `0.35 ATR` through the level;
- directional body and close-location requirements remain unchanged.

## BF2B-09 — Broader impulse-pause continuation

IDs: `GML1-BF2B-09-L`, `GML1-BF2B-09-S`

- impulse body minimum: `0.65 ATR`;
- impulse close location: 0.70/0.30;
- pause range maximum: `0.85 ATR`;
- pause remains in the directional 55% of the impulse range;
- continuation close exceeds pause extreme by `0.03 ATR`.

## BF2B-14 — Broader previous-day sweep recovery

IDs: `GML1-BF2B-14-L`, `GML1-BF2B-14-S`

- price must trade beyond the last closed D1 high/low, with no extra 0.05 ATR penetration requirement;
- wick minimum: 30% of range;
- close location: 0.60/0.40;
- permissive reversal context remains unchanged.

## BF2B-15 — Broader previous-day breakout acceptance

IDs: `GML1-BF2B-15-L`, `GML1-BF2B-15-S`

- breakout distance: `0.05 ATR`;
- signed-body minimum: `0.25 ATR`;
- close location: 0.65/0.35;
- prior-close and continuation-context requirements remain unchanged.

## BF2B-16 — Broader previous-day breakout retest

IDs: `GML1-BF2B-16-L`, `GML1-BF2B-16-S`

- setup is BF2B-15;
- search window: eighteen M5 bars;
- retest may come within `0.10 ATR` of the frozen level;
- confirmation must close on or beyond the level with correctly signed body;
- invalidation: `0.25 ATR` through the level.

## BF2B-17 — Broader closed-H1 boundary rejection

IDs: `GML1-BF2B-17-L`, `GML1-BF2B-17-S`

- price must trade beyond the prior closed-H1 20-bar boundary, with no extra 0.05 M5 ATR penetration;
- wick minimum: 30%;
- close location: 0.60/0.40;
- permissive reversal context remains unchanged.

## BF2B-18 — Broader high-volatility exhaustion recovery

IDs: `GML1-BF2B-18-L`, `GML1-BF2B-18-S`

- lagged ATR percentile minimum: 0.70;
- range minimum: `1.30 ATR`;
- four-bar displacement minimum magnitude: `0.75 ATR`;
- wick minimum: 35%;
- close location: 0.60/0.40;
- permissive reversal context remains unchanged.

## Controls

- No label, outcome, WR, PF, R, exit or future bar was used to create these variants.
- The V2 and V2B candidates are separate IDs and will be reported separately.
- No later density revision is allowed after label join.
- Live, final signal, Discord and MT5 controls remain OFF.
