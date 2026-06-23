# GOLD V3 Stage308 - Mochipoyo Method Walk-Forward (Audit Only)

## Status

- Research only.
- No production promotion.
- Stage280 remains blocked and unchanged.
- Stage281 and Stage286 remain unchanged.
- MT5 automatic order, Discord and partial close remain disabled.

## Purpose

Translate the discretionary method described in the supplied Mochipoyo master guide into closed-candle, auditable research rules that can contribute independent GOLD candidates.

The proprietary Mochipoyo alert formula is not disclosed in the guide. Stage308 does not claim to reproduce that alert. It implements the documented top-down trading method around the alert: higher-timeframe context, EMA direction, RCI, MACD divergence, volatility, pullback/retest and structural risk management.

## Timeframe pairs

- M5 main / H4 context
- M15 main / H4 context
- H1 main / D1 context

Only closed candles are used. The higher-timeframe row is joined by `close_time <= main close_time`. Entry is the next exact main-timeframe open.

## Indicators

- EMA: 20, 30, 40
- RCI: 9, 14, 18
- MACD: 6, 13, 4
- ATR: 14
- Confirmed ZigZag approximation: Depth 5, Deviation 3 broker points, Backstep 2

A ZigZag pivot becomes usable only after five later bars have closed. This prevents unconfirmed-pivot leakage.

## Candidate families

### Trend continuation

Core requirements:

- Higher-timeframe EMA20/30/40 alignment in the trade direction.
- Main-timeframe EMA20/30/40 alignment in the trade direction.
- High-volatility gate.

Confluence score adds:

- Higher-timeframe RCI turn or hidden divergence.
- Main-timeframe RCI extreme-zone turn.
- MACD re-acceleration.
- Pullback to EMA20.
- Hidden divergence.
- Roll-reversal/retest.
- Round-number proximity as bonus only.

Variants:

- `TREND_SCORE6`
- `TREND_SCORE7`
- `HIDDEN_SCORE6` (hidden divergence required)

### Reversal

Core requirements:

- Higher-timeframe RCI turn.
- Main-timeframe RCI turn.
- Regular MACD divergence on main or higher timeframe.
- High-volatility gate.

Variant:

- `REVERSAL_SCORE6`

## Volatility

Low-volatility congestion is excluded. The gate uses both:

- ATR14 relative to its closed rolling median.
- Width of the latest confirmed ZigZag wave relative to ATR14.

## Risk and exits

Stop:

- Latest confirmed ZigZag swing plus 0.10 ATR buffer.
- Minimum stop distance 0.75 ATR.
- Candidate skipped if structural stop exceeds 2.0 ATR.

Exit profiles:

- RR 1.0
- RR 1.5
- Confirmed RCI9 arrival at the opposite +/-70 zone
- Opposite confirmed structural swing target, only when natural RR is at least 1.0

M1 resolves SL/TP first touch. Same M1 bar gives SL priority. Spread is converted from MT5 points with `point_size=0.01`.

## Evaluation

Years:

- 2024
- 2025
- 2026 YTD

Metrics remain separated by family, exit profile, year and one-position portfolio. Raw trades are exported for later overlap analysis.

Balanced gate:

- At least 75 trades total.
- At least 12 trades in each year.
- Win rate at least 50%.
- Spread-adjusted PF at least 1.30.
- Positive spread-adjusted total R.
- Spread-adjusted max DD no more than 12R.
- Worst year above -1R.

High-frequency gate:

- At least 150 trades total.
- At least 20 trades in each year.
- Win rate at least 48%.
- Spread-adjusted PF at least 1.20.
- Positive spread-adjusted total R.
- Spread-adjusted max DD no more than 16R.
- Worst year above -1R.

## Outputs

- `stage308_mochipoyo_method_walkforward.json`
- `stage308_mochipoyo_method_walkforward_trades.csv`

## Next step after a pass

Do not activate directly. First run integrated overlap, priority and drawdown replay against the Stage307 top ensemble and the existing Stage292 candidates. Freeze a new model identity only after that replay passes.
