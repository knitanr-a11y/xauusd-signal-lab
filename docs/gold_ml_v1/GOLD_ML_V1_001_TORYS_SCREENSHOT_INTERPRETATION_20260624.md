# GOLD ML V1 — TORYS Screenshot Interpretation

Date: 2026-06-24  
Status: `TORYS_VISIBLE_SETTINGS_CAPTURED`

The uploaded settings screenshots are sufficient to begin a TORYS-inspired feature implementation.

Confirmed visible values:

- Display label: ON
- Hidden trend only: ON
- Trend strength: 4
- Length to finalize / offset: 2
- Period to recognize vertices: 10
- Number of vertices: 6
- Number of candlesticks: 150
- Price source: close
- MACD source: close
- Fast EMA length: 6
- Slow EMA length: 13
- Signal length: 4
- Judge trend: EMA
- MA source: close
- MA lengths: 10, 15, 30, 40, 60
- Highest/Lowest plot: ON
- Previous Highest/Lowest plot: ON
- Connect Highest/Lowest: OFF
- Display trend zone: OFF
- Divergence L-L alert source UI value: high
- Divergence H-H alert source UI value: low
- Display bgcolor for alert No.5: OFF

Research interpretation:

1. The base MACD line may be implemented as `EMA(close,6)-EMA(close,13)`.
2. The screenshots do not expose the source code, so exact internal signal smoothing cannot be proven.
3. The primary research proxy will use `EMA(MACD line,4)`.
4. A separate `SMA(MACD line,4)` proxy may be tested under a different feature-set ID.
5. `Judge trend = EMA` is treated as the trend-judgement method using close-based MA lengths 10/15/30/40/60. It is not assumed to define the MACD signal-line smoothing.
6. The confirmed vertex settings may be used to build a TORYS-inspired divergence feature family.
7. Display and plot options are visual settings, not entry conditions.
8. Because the project is searching for profitable shapes rather than reproducing the original alert, exact TORYS replication is not required.

Machine-readable settings:

`config/gold_ml_v1/torys_visible_settings_20260624.json`
