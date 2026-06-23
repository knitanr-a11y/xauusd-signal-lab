# GOLD V3 Stage291 — Stage286 external M15 live connection

## Purpose

Connect the actual MT5 Files outputs below to the Stage286 strict SHORT candidate detector.

- `us500cashsharp_m15.csv` from broker symbol `US500Cash#`
- `us100cashsharp_m15.csv` from broker symbol `US100Cash#`

The existing GOLD files remain unchanged.

## Contracts

- CSV latest row is closed by the exporter contract.
- `time` is the MT5 server bar-open time.
- Each external M15 row becomes available only at `time + 15 minutes`.
- Stage286 uses only external rows available at the GOLD decision time.
- US500 and US100 must have the same latest M15 timestamp.
- Conflicting duplicate OHLC rows are blocked.
- A minimum of 20 rows is required; the live exporter currently provides 30,000.

## Stage286 fixed gate

- H4 trend = up
- GOLD M15 ret8/ATR >= `2.162461836828524`
- GOLD M15 ret8/ATR <= `2.992581130893`
- GOLD M15 position in last 4 bars >= `0.75`
- upper wick ratio >= lower wick ratio
- mean(US500 M15 ret4/ATR, US100 M15 ret4/ATR) <= `0.410970621210`
- all required features finite

No threshold is re-selected from live data.

## Live trigger

The SHORT EMA20 trigger is evaluated on closed GOLD M5 bars.

The monitor does not wait for a future M5 row. When a trigger bar closes:

- `trigger_dt` = trigger bar open time
- `planned_entry_dt` = trigger bar close time
- `reference_price` = trigger bar close

The actual execution price is not invented by this monitor.

## Outputs

Default directory:

`MQL5/Files/FX_OUTPUTS/gold_v3/291_stage286_external_live_m15/`

Files:

- `gold_v3_291_external_m15_validation.csv`
- `gold_v3_291_stage286_latest_gate_snapshot.csv`
- `gold_v3_291_stage286_live_candidates.csv`
- `gold_v3_291_stage286_latest_live_candidate.csv`
- `gold_v3_291_summary.json`

Every candidate records:

- US500 source bar time and ret4/ATR
- US100 source bar time and ret4/ATR
- their mean
- GOLD exhaustion score and wick/position features
- planned entry time and reference price

## Run

Windows:

`scripts/gold_v3_runtime/bat/run_gold_v3_291_stage286_external_live_monitor.bat`

The script reads the existing Files directory. It does not send MT5 orders and does not send Discord notifications.
