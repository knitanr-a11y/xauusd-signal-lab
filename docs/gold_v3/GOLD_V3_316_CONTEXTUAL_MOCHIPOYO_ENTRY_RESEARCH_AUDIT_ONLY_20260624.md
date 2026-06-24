# GOLD V3 Stage316 — Contextual Mochipoyo Entry Research

## Purpose

Stage316 tests the user's hypothesis directly: Mochipoyo signals may work better when market regime and entry timing are separated from the initial alert.

The study does not treat every Mochipoyo alert as an immediate entry. It first detects the original Mochipoyo setup, then waits for a closed-candle confirmation inside a fixed number of bars, and only then enters at the next exact main-timeframe open.

## Base signal layer

The original Stage311 Mochipoyo tracks are retained unchanged as the alert layer:

- `MOCHI_EARLY_PULLBACK`
- `MOCHI_HIDDEN_PULLBACK`
- `MOCHI_HTF_RCI_RESUME`
- `MOCHI_ROLL_RETEST`

## Market-regime and entry-confirmation recipes

### `MIDTREND_RECLAIM`

Regime:

- higher and lower timeframe trend aligned
- ADX14 between 18 and 42
- ATR ratio between 0.85 and 1.55
- moderate EMA20 extension
- climax candle excluded

Confirmation:

- EMA20 reclaim
- RCI turn or MACD acceleration
- directional body and directional close strength

### `EXPANSION_MICROBREAK`

Regime:

- higher and lower timeframe trend aligned
- ATR expansion with rising ADX
- recent compression or inside-bar structure
- late extension and climax excluded

Confirmation:

- close beyond the previous three-bar extreme
- RCI, MACD, or higher-timeframe RCI confirmation
- directional body and strong close position

### `PULLBACK_STRUCTURE_BREAK`

Regime:

- higher-timeframe trend aligned
- pullback, recent pullback, or EMA40-area deep touch
- controlled ADX and ATR range
- entry not excessively extended

Confirmation:

- close beyond both the original signal-bar structure and recent three-bar structure
- RCI turn or MACD acceleration

### `IMPULSE_RESUME`

Regime:

- higher and lower timeframe trend aligned
- ADX at least 18
- ATR ratio between 0.90 and 1.60
- late extension and climax excluded

Confirmation:

- three consecutive directional candles
- at least 0.80 ATR combined directional body

## Confirmation waiting window

- M5/H4: up to four closed M5 bars
- M15/H4: up to three closed M15 bars
- H1/D1: up to two closed H1 bars

The confirmation search begins one bar after the original Mochipoyo signal. If no confirmation appears inside the fixed window, no trade is taken.

## Entry and exit

- entry: next exact main-timeframe open after the closed confirmation bar
- stop: confirmed ZigZag structural stop with the existing 0.10 ATR buffer
- minimum stop: 0.75 ATR
- maximum stop: 2.0 ATR
- exits: 1.25R and 1.50R
- M1 first-touch resolution
- same-M1 TP/SL collision: SL priority

## Selection protocol

- 2024 and 2025 only for selection
- 2026 display only
- Stage311 research gate unchanged
- no threshold selection from 2026

Stage316 also compares every contextual family with its corresponding immediate-entry Stage311 family using 2024–2025 only.

A contextual-value pass requires:

- the contextual family passes the unchanged Stage311 gate
- contextual PF is not below the immediate-entry baseline
- minimum yearly PF is not below the baseline
- contextual drawdown is no more than 1R worse than the baseline

This avoids calling a lower-frequency filter an improvement merely because it removes many trades.

## Outputs

- `stage316_contextual_mochipoyo_entry_research.json`
- `stage316_contextual_mochipoyo_all_trades.csv`
- `stage316_selected_contextual_mochipoyo_trades.csv`

The result also reports holding-period overlap with:

- Stage307 top candidate
- Stage313 Mochipoyo historical watch
- Stage315 independent selected portfolio

## Preserved state

- GOLD V3 audit-only
- Stage314 future-only prospective contract unchanged
- Stage315 independent research unchanged
- Stage280 exact recovery remains blocked
- Stage307 top candidate unchanged
- Stage292 candidate pool unchanged
- final signal unchanged
- MT5 automatic order OFF
- Discord OFF
- partial close OFF
