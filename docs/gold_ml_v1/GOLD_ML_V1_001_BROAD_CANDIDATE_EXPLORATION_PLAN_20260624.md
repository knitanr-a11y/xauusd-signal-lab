# GOLD ML V1 — Broad Candidate Exploration Plan

Date: 2026-06-24

Status: `SEARCH_PLAN_DEFINED_NOT_YET_EXECUTED`

## Objective

Find and accumulate multiple independent candidates for GOLD# without replacing an existing candidate or mixing portfolio results into standalone candidate results.

## Independent axes

Every result is separated by:

- timeframe lane: M1-H1, M5-H4, M15-H4, or H1-D1;
- direction: LONG or SHORT;
- label and exit definition;
- feature-set ID;
- model ID;
- threshold and entry policy.

## Search families

The search will include:

1. higher-timeframe trend with lower-timeframe pullback continuation;
2. breakout continuation after compression;
3. breakout-level retest and roll reversal;
4. failed breakout reversal;
5. regular MACD or RCI divergence reversal;
6. hidden divergence continuation;
7. RCI extreme reversal and multi-line RCI state;
8. EMA ordering, slope, compression, expansion, reclaim, and rejection;
9. causal short and medium ZigZag structure;
10. volatility expansion, compression, high-volatility trend, and exhaustion;
11. range-edge mean reversion;
12. MT5-server-time and session specialists;
13. round-number, prior-day, prior-week, and past support/resistance context;
14. candle range, body, wick, tick-volume, and spread context;
15. non-Mochipoyo data-driven discovery.

## Model order

The search proceeds from simple to complex:

1. label and timestamp sanity checks;
2. logistic and regularized linear baselines;
3. gradient-boosted tree models;
4. one setup family at a time;
5. controlled feature interactions;
6. trend, range, volatility, and time specialists;
7. sequence models only after causal tabular baselines are established.

## Overfitting controls

- walk-forward validation;
- embargo between splits;
- final holdout never used for search or threshold selection;
- every attempted configuration logged, including failures;
- confidence intervals and minimum sample requirements;
- cost and spread stress tests;
- parameter-neighborhood tests;
- year, quarter, session, volatility, and regime breakdowns;
- largest-winner and event-cluster concentration checks;
- no candidate registration from one favorable subperiod alone.

## Candidate registration

A passing candidate receives an immutable candidate ID with:

- one lane;
- one direction;
- one label ID;
- one feature-set ID;
- one model ID;
- exact threshold;
- exact standalone trade registry;
- cost-adjusted metrics and confidence intervals;
- data, code, and configuration hashes.

Changing any item creates a new candidate. Portfolio work begins only after standalone candidates are registered.

## Current boundary

The breadth of the search is now defined. Actual training and candidate search begin only after the Phase001 dataset split, embargo, feature registry, label registry, cost conversion, and local dataset audit are frozen.
