# Stage M7A — Alert Trigger Signature Audit Contract

Status: audit-only  
Contract version: `MOCHIPOYO_M7A_TRIGGER_SIGNATURE_V1`

## Purpose

Stage M7A tests which causal, independently calculated conditions distinguish genuine Mochipoyo events from M15 bars where no event was received.

It does **not** claim to recover the proprietary source code or exact internal formula. The output is an independent trigger proxy discovery report.

A later stage may freeze a proxy and scan older history or other timeframes only after forward validation against later genuine events.

## Positive labels

Positive labels are genuine Webhook / SQLite source events only.

The six transition targets are analyzed separately:

- `PRIMARY_LONG`: `IDLE -> LONG`
- `PRIMARY_SHORT`: `IDLE -> SHORT`
- `REENTRY_LONG`: `ACTIVE_LONG -> LONG`
- `REENTRY_SHORT`: `ACTIVE_SHORT -> SHORT`
- `LONG_EXIT`: `ACTIVE_LONG -> LONG_EXIT`
- `SHORT_EXIT`: `ACTIVE_SHORT -> SHORT_EXIT`

State is part of target eligibility. For example, an IDLE M15 bar is not a negative control for `LONG_EXIT` because a long exit is not eligible in IDLE state.

## Negative controls

A missing event is treated as a negative control only inside the conservative verified window from the first genuine event boundary to the last genuine event boundary for the same ticker.

M15 bars before Webhook observation began and bars after the last observed source event are not silently labeled negative.

This prevents old historical CSV rows, from periods where source alerts were not being recorded, from becoming false negatives.

## Decision-time contract

The source label is normally drawn on the new M15 bar. Therefore:

- decision time is the current M15 bar open;
- features come from the last fully closed M15 bar;
- the current M15 open may be used because it is known at decision time;
- current-bar high, low, and close are forbidden;
- future bars are forbidden.

The all-bar decision mapping must reproduce every event's already-audited Stage M4 M15 selected bar. Any mismatch fails closed.

## Independent features

Stage M7A calculates causal features from MT5 M15 CSV data:

- EMA 20 / 30 / 40 alignment, distance, spread, and slope;
- RCI 9 / 14 / 18 level, one-bar change, ±80 crossing, and turn proxies;
- MACD 6 / 13 / 4 level, histogram change, zero cross, and turn proxies;
- ATR14 and candle range;
- candle body and wick ratios;
- tick-volume ratio;
- 5 / 10 / 20-bar range position;
- independent causally confirmed short/medium pivot proxies;
- current-open gap and open-to-EMA distance;
- prior source transition, bars since the previous event, and active-state age.

These are independent calculations. They are not copied proprietary indicator values.

## Rule discovery

For each transition and for each scope (`ALL`, `XAUUSD`, `BTCUSD`), Stage M7A reports:

- event count and eligible decision count;
- base event rate;
- single-condition threshold/equality signatures;
- two-condition intersections;
- precision, recall, lift, F1, matched events, and matched controls;
- event-vs-control feature contrasts.

The search is transparent and shallow. It is intended to show candidate trigger signatures rather than hide overfitting inside a complex model.

## Sample-size restriction

Current genuine event counts are small. Even a rule matching every current event can be one of many incompatible formulas that happen to fit the same short window.

Therefore all discovered rules remain:

- `EXPLORATORY_ONLY`, or
- `VERY_SMALL_SAMPLE`.

The following stay false:

- exact internal condition identified;
- historical candidate extraction approved;
- cross-timeframe extraction approved;
- automatic trading rule approved.

## Outputs

The runner writes:

- `latest_alert_trigger_signature_audit.json`
- `latest_alert_trigger_event_features.csv`
- `latest_alert_trigger_candidate_rules.csv`

Input MT5 CSV files and SQLite source/upstream tables are not modified.

## Next-stage condition

Stage M7B may be designed only after M7A results are reviewed.

M7B must:

1. select a small number of interpretable proxy candidates;
2. freeze their formulas before looking at later source events;
3. measure recall and false-positive rate on later genuine alerts;
4. keep proxy-generated rows labeled separately from genuine Mochipoyo alerts;
5. only then consider full-history and cross-timeframe candidate scans.

## Safety

The following remain disabled:

- entry gate
- historical replay approval
- cross-timeframe replay approval
- Discord sending
- MT5 order placement
- live-ready state
- final signal
