# GOLD ML V1 — Dual ZigZag Screenshot Interpretation

Date: 2026-06-24  
Status: `DUAL_ZIGZAG_VISIBLE_SETTINGS_CAPTURED`

The screenshot confirms that the user's chart uses two ZigZag scales.

## Visible settings

### ZigZag 1 — short swing

- Display: ON
- Depth: 5
- Deviation: 3
- Backstep: 2
- Line width: 2
- Label: OFF
- Label size: tiny
- Repaint Levels: ON
- Extend ZigZag: OFF

### ZigZag 2 — medium swing

- Display: OFF
- Depth: 12
- Deviation: 5
- Backstep: 3
- Line width: 2
- Label: ON
- Repaint Levels: ON
- Extend ZigZag: OFF

The first scale is interpreted as short-wave structure and the second as a slower structural wave. Display status is not a research rule: the second scale can still be useful as a feature even when hidden on the chart.

## Critical repaint boundary

Both ZigZags have `Repaint Levels` enabled.

A repainting ZigZag may move or remove its most recent pivot after later candles arrive. A historical chart can therefore show a pivot at an earlier candle even though that pivot was not knowable at that time.

The new project must never use the final plotted historical ZigZag path as if it had been available in real time.

For every pivot, preserve two times:

- `pivot_bar_time`: the candle on which the price extreme occurred;
- `pivot_confirmation_time`: the later closed-candle time at which the pivot became usable.

Features and decisions may use the pivot only from `pivot_confirmation_time` onward.

The current unconfirmed endpoint is forbidden as a model input.

## Exact-reproduction boundary

The screenshot does not identify the indicator source code or the exact unit and implementation of `Deviation`.

Therefore the project must not claim exact visual reproduction.

The visible values are preserved, but causal research variants will be implemented as separate feature sets, including:

1. confirmed depth/backstep pivot proxy;
2. ATR-threshold swing proxy;
3. percentage-threshold swing proxy.

Each variant receives a different feature-set ID. Their results cannot be combined or renamed as one feature set.

## Useful features

The two scales can provide:

- direction of the last confirmed swing;
- last confirmed pivot price;
- bars elapsed since confirmation;
- swing size in price and ATR units;
- swing duration;
- pullback and extension ratios;
- higher-high, higher-low, lower-high, and lower-low state;
- fast/slow ZigZag directional agreement;
- small pullback nested inside a larger trend;
- distance to prior breakout or roll-reversal level;
- distance from a confirmed pivot to round numbers;
- RCI divergence measured only between confirmed pivots;
- MACD divergence measured only between confirmed pivots.

## Independent research lineages

The following are separate lineages:

- fast ZigZag only;
- slow ZigZag only;
- fast and slow alignment;
- fast counter-swing inside slow trend;
- LONG and SHORT versions;
- each timeframe lane;
- each ZigZag algorithm variant.

Adding ZigZag does not alter or replace any other candidate. It only creates additional feature families and later, if validated, additional immutable candidates.

Machine-readable settings:

`config/gold_ml_v1/zigzag_visible_settings_20260624.json`
