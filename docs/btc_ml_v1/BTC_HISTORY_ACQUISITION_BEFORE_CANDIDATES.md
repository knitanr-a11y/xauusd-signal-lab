# BTCUSD# MT5 history acquisition before candidate discovery

## Status

`BTC_HISTORY_ACQUISITION_BEFORE_CANDIDATE_DISCOVERY`

The exact broker symbol is fixed as:

```text
BTCUSD#
```

This stage prepares independent BTC data before candidate discovery. It does not use GOLD candidate IDs, thresholds, directions, target R, holding periods, win rates, lot size, magic numbers or output state.

The exporter contains no order-send or Discord-send path. The following remain off:

- `live_ready = false`
- `final_signal = false`
- Discord
- MT5 orders
- BTC strategy registration
- BTC candidate selection from outcomes

## Files created

The default output is the repository `Files` directory:

```text
Files/btcusdsharp_m1.csv
Files/btcusdsharp_m5.csv
Files/btcusdsharp_m15.csv
Files/btcusdsharp_h1.csv
Files/btcusdsharp_h4.csv
Files/btcusdsharp_d1.csv
Files/btcusdsharp_history_manifest.json
```

Every CSV uses this canonical schema:

```text
time,open,high,low,close,tick_volume,spread,real_volume
```

`time` is UTC represented without a timezone suffix. It is derived directly from the MT5 Unix epoch. All six files use the same basis.

## Closed-row contract

Only bars satisfying the following rule are written:

```text
bar open epoch + timeframe duration <= export snapshot UTC
```

The current/open MT5 bar is therefore excluded. The latest output row is closed by contract. No future high, low, close, ATR, TP/SL result or unresolved horizon is created or used.

## Existing BTC CSV protection

The exporter does not append directly to the current files.

1. Every requested timeframe is downloaded into a staging directory.
2. Each staged file must contain at least one closed bar.
3. Only after all requested timeframes succeed are the current files copied to:

```text
Files/btcusdsharp_backups/<UTC timestamp>/
```

4. Staged files then replace the selected current files using `os.replace`.
5. If download or validation fails before commit, the existing CSV files are not replaced.

The old files remain available in the backup directory for comparison or recovery.

## MT5 preparation

Use the same MT5 terminal and account intended for BTC data collection.

Before exporting a large history:

1. Open MT5.
2. Confirm `BTCUSD#` is visible in Market Watch.
3. Open **Tools → Options → Charts**.
4. Set **Max bars in chart** as high as the terminal allows, preferably Unlimited.
5. Restart MT5 if the setting was changed.
6. Open BTCUSD# charts once for the required timeframes if the broker needs to download history on demand.

Python requirements:

```text
MetaTrader5
numpy
```

## Run all timeframes

From the repository root:

```bat
scripts\btc_ml_v1\data_history\run_export_btcusdsharp_history.bat
```

The default requested start is `2017-01-01 UTC`; the broker returns only history that actually exists for `BTCUSD#`.

## Specify the start date

```bat
scripts\btc_ml_v1\data_history\run_export_btcusdsharp_history.bat --start 2020-01-01
```

## Export selected timeframes only

```bat
scripts\btc_ml_v1\data_history\run_export_btcusdsharp_history.bat --timeframes M1 M5 M15
```

Unselected current files are left untouched.

## Optional MT5 connection settings

The exporter accepts:

```text
--terminal-path
--login
--password
--server
--output-dir
--start
--end
--timeframes
```

It also reads the BTC-only environment names:

```text
BTC0_MT5_TERMINAL_PATH
BTC0_MT5_LOGIN
BTC0_MT5_PASSWORD
BTC0_MT5_SERVER
```

Do not commit credentials.

## Manifest checks before candidate discovery

Review:

```text
Files/btcusdsharp_history_manifest.json
```

For each timeframe confirm:

- `rows`
- `first_time_utc`
- `last_time_utc`
- `research_minimum_met`
- `gaps_over_one_bar`
- `maximum_gap_seconds`
- `sha256`

The initial research row targets are diagnostics, not signal conditions:

```text
M1   100000
M5    30000
M15   10000
H1     5000
H4     1000
D1      365
```

If a target is not met, increase MT5 history availability or document the broker limitation before candidate exploration.

## Next stage

After the user-PC export result is inspected, the next work is BTC historical data audit and label-free candidate-density exploration. Candidate conditions must be created from BTC data only. Final evaluation outcomes must not be used to choose conditions, and all future health/rolling gates must use only results resolved by the current entry time.
