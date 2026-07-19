# Stage M6C — Causal M5 Entry Timing Audit Contract

Status: audit-only  
Contract version: `MOCHIPOYO_M6C_M5_ENTRY_TIMING_V1`

## Purpose

Stage M6C tests whether the Mochipoyo source alert is better used as:

- an immediate entry reference,
- a closed-M5 directional confirmation,
- a closed-M5 structure break,
- a pullback followed by a structure break, or
- a causal second-bottom / second-top confirmation.

This stage does not approve a trading rule.

## Event identity

Primary and reentry events are identified by the Webhook / SQLite source event ID.

A chart label does not need to move or redraw when a reentry alert is received.

## Upstream requirements

M6C fails closed unless all of the following are current and internally consistent:

1. Stage M3 primary and reentry event assignments.
2. Stage M4 M5 alignment and per-event MT5 offset.
3. Stage M5 causal feature snapshots for M5/M15/H1/H4/D1.
4. Stage M6A source entries and closed/open accounting.

If new alerts have been collected but upstream stages were not rebuilt, M6C stops instead of silently omitting them.

## Price-basis contract

TradingView source prices and MT5 delayed-entry prices are not mixed inside the paired timing comparison.

All timing variants use an MT5-only comparison basis:

- reference entry:
  first M1 open strictly after the source event minute;
- delayed M5 entry:
  the close of the fully closed M5 trigger bar;
- exit reference:
  the final fully closed M1 close before the source EXIT minute.

The original TradingView source price is retained only as source-event metadata.

## Reference entry

`SOURCE_NEXT_M1_OPEN_REFERENCE`

The complete minute containing the source event is excluded.

The reference entry is the next available MT5 M1 open strictly after that minute.

This is a conservative executable-price reference, not a claim that the real source alert could only be entered one minute later.

## M5 variants

### `M5_FIRST_DIRECTIONAL_BODY_CLOSE`

First post-alert fully closed M5 candle whose body points in the source direction:

- LONG: close > open
- SHORT: close < open

Entry reference is the trigger candle close.

### `M5_TWO_BAR_BREAK_CLOSE`

First post-alert fully closed M5 candle whose close breaks the prior two completed M5 bars:

- LONG: close > maximum prior-two high
- SHORT: close < minimum prior-two low

No pullback is required.

### `M5_PULLBACK_THEN_TWO_BAR_BREAK_CLOSE`

Uses the same two-bar break, but only after an adverse closed-M5 close relative to the MT5 reference entry:

- LONG pullback: M5 close below MT5 reference price
- SHORT pullback: M5 close above MT5 reference price

### `M5_SECOND_BOTTOM_TOP_BREAK_CLOSE`

Independent causal structure proxy:

- pivot left bars: 2
- pivot right confirmation bars: 2
- LONG: a second confirmed low must be greater than or equal to the first confirmed low
- SHORT: a second confirmed high must be less than or equal to the first confirmed high
- after the second pivot is confirmed, a fully closed M5 candle must break the neckline

The entry reference is the neckline-break candle close.

This is not a proprietary indicator clone.

## Causality

Candidate detection may use only bars fully closed by the candidate decision time.

The outcome, source EXIT result, MFE, and MAE are not used to detect a candidate.

Post-entry bars are used only after candidate detection to measure the hypothetical outcome.

## Outcome measurement

For a detected candidate in a closed source episode:

- direction-adjusted return is measured to the MT5 exit reference;
- MFE and MAE use MT5 M1 OHLC from candidate entry time to the exit reference;
- 1 M5 ATR is used as the descriptive expansion threshold;
- no TP or SL is applied;
- no position size or USD P/L is defined.

## Paired comparison

Each delayed candidate is paired with the same source event's MT5 reference entry.

Reported deltas include:

- return ATR difference versus reference;
- MAE ATR difference versus reference;
- candidate price improvement versus reference;
- entry delay;
- candidate detection / missed count.

A negative MAE delta means the delayed entry reduced adverse excursion.

## Open episodes

Candidate detection can be recorded for an open source episode up to the latest closed M5 bar.

No resolved outcome is created until the source EXIT is received.

## Sample-size policy

Current results remain descriptive.

No threshold is optimized on the current sample.

Cohorts are labeled:

- `<5`: `VERY_SMALL_SAMPLE`
- `<20`: `SMALL_SAMPLE`
- `<50`: `OBSERVATION_SAMPLE`
- otherwise: `RULE_DESIGN_SAMPLE`

## Safety

The following remain disabled:

- entry gate
- automatic rule approval
- Discord sending
- MT5 order placement
- live-ready state
- final signal

Derived M6C tables may be rebuilt atomically. Raw alerts, episodes, alignments, feature snapshots, M6A virtual entries, and M6A outcomes are not modified.
