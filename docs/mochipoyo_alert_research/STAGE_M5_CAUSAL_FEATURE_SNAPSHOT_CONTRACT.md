# Mochipoyo Stage M5 causal feature snapshot contract

Status: `MOCHIPOYO_M5_CAUSAL_FEATURE_SNAPSHOTS_AUDIT_ONLY`

## Purpose

Create one immutable analysis snapshot for each eligible real Mochipoyo alert and each aligned MT5 context timeframe:

- M5
- M15
- H1
- H4
- D1

The snapshot describes only information available at the TradingView alert decision time. It is not an entry gate, final signal, order instruction, or reconstruction of the private Mochipoyo indicator.

## Required upstream state

Stage M5 fails closed unless all of the following are true:

1. The user-confirmed connection-test alert ID 1 is excluded through `raw_alert_annotations`.
2. Every current eligible raw alert is mapped to an episode event.
3. Stage M4 contains exactly one `ALIGNED_CLOSED_BAR` row for each eligible alert and each of the five timeframes.
4. The selected MT5 bar still exists in the configured CSV.
5. The selected bar OHLC still matches the Stage M4 audit record.
6. The selected bar UTC close is not later than the TradingView decision time.
7. At least 50 closed bars are available through the selected bar.

A newly collected alert without a refreshed Stage M4 alignment causes Stage M5 to stop instead of silently omitting that alert.

## Stored indicators and context

Each `features_json` contains:

- EMA 20 / 30 / 40 values, ordering, spread, distance from close, and three-bar slopes
- RCI 9 / 14 / 18 values and independent ±80 flags
- MACD 6 / 13 / 4 on close, including line, signal, histogram, normalized values, and zero proximity relative to ATR
- Wilder ATR14 and true range
- Current candle body and wick ratios
- Tick-volume ratio against the most recent 20 closed bars
- Highest high, lowest low, range, close position, and distances for 5 / 10 / 20 closed bars
- Independent causal pivot proxies referencing the short 5 / 3 / 2 and medium 12 / 5 / 3 settings
- Source-history prefix SHA-256 through the selected bar
- Selected MT5 server open, estimated UTC open/close, decision time, offset used, and bar age

## ZigZag safety contract

The project does not clone the private indicator or assume exact MT5/proprietary point-based deviation behavior.

The stored ZigZag fields are independent delayed-confirmation pivot proxies:

- short proxy: depth 5, deviation reference 3, right confirmation 2 bars
- medium proxy: depth 12, deviation reference 5, right confirmation 3 bars

A pivot is stored only after its required right-side confirmation bars are already closed by the decision time. No bar after the decision cutoff participates. The point-based deviation rule is explicitly marked as not applied.

## Indicator implementation contract

- EMA: recursive `alpha = 2 / (period + 1)`, seeded with the first CSV close
- ATR14: Wilder smoothing, seeded with the first 14 true ranges
- RCI: Spearman rank correlation with average ranks for tied closes
- MACD: EMA6 minus EMA13, signal EMA4, close source
- Recent ranges include the selected closed bar

These are independent research calculations. Small differences from TradingView, MT5, TORYS, or the private Mochipoyo display are not treated as evidence that the source alert was wrong.

## No-future contract

For every row:

```text
latest_closed_bar_time <= knowledge_cutoff_utc
knowledge_cutoff_utc = TradingView fired_at_utc
future_fields_present = 0
```

Appending a later CSV bar must not change a historical snapshot, except for the audit build timestamp which is not a market feature.

EXIT information, MFE, MAE, later pivots, later higher-timeframe states, and outcome labels are not read by Stage M5.

## Atomic rebuild and dependency invalidation

All 205 current snapshots are calculated and validated before the replacement transaction begins. A pre-transaction failure preserves the previous successful snapshot table.

SQLite triggers remove dependent feature snapshots when:

- their episode is deleted during a later Stage M3 rebuild, or
- their Stage M4 alignment row is deleted during a later alignment rebuild.

This prevents stale feature rows from surviving a changed episode or time-alignment contract.

## Safety state

```text
audit_only = true
dry_run = true
entry_gate_enabled = false
proprietary_indicator_reconstruction = false
future_outcomes_used = false
discord_send = false
mt5_order = false
live_ready = false
final_signal = false
```

## Windows execution

After Stage M4 has been rebuilt for all current alerts, run:

```text
scripts\mochipoyo_alert_research\run_build_feature_snapshots_once.bat
```

For 41 eligible alerts and five timeframes, the expected result is:

```text
eligible_alert_count = 41
expected_snapshot_count = 205
snapshot_count = 205
warmup_insufficient_count = 0
future_violation_count = 0
```

The local report is written to:

```text
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\logs\latest_feature_snapshot_build_result.json
```
