# BTC-0 broker and data contract audit

## Status

`BTC-0_BROKER_AND_DATA_CONTRACT_AUDIT_ONLY`

This stage only reads the user's MT5 terminal and existing BTC CSV files. It does not create candidates, signals, Discord notifications or MT5 orders.

The following remain disabled and undecided:

- `live_ready = false`
- `final_signal = false`
- Discord delivery
- dry-run or real-order execution
- BTC magic numbers and MT5 comment prefixes
- BTC lot size and risk sizing
- BTC entry direction, SL/TP, target R and holding horizon

GOLD values, candidate IDs, thresholds, results, `GOLD#`, `0.01` lot, magic numbers and output files are not imported.

## Purpose

The audit determines the broker-specific BTC contract before any BTC signal research begins:

- exact symbol name, without assuming `BTCUSD`;
- digits and point size;
- contract size;
- minimum, step and maximum volume;
- tick size and tick value;
- current and historical spread units;
- allowed filling, trade and order modes;
- minimum stop and freeze distances;
- observed weekend and weekday/hour availability;
- available closed M1/M5/M15/H1/H4/D1 history depth;
- existing BTC CSV inventory and timestamp range.

The minimum-volume 1% adverse-move estimate uses MT5 `order_calc_profit` as a read-only calculation. It is evidence for later risk review, not permission to trade that volume.

## Closed-row contract

Two data sources are treated differently and explicitly:

1. MT5 `copy_rates_from_pos(..., start_pos=0)` may include the current open bar. BTC-0 always removes the newest returned MT5 bar before computing history depth, spread or observed trading hours.
2. Existing BTC CSV files follow the repository contract: their latest stored row is treated as closed. BTC-0 inventories that row but does not create signals from it.

No future TP/SL outcome, unresolved horizon result, future high/low/close or open candle is used.

## Requirements on the user PC

Use the same Windows PC and MT5 terminal/account that may eventually host BTC. Python needs:

```text
MetaTrader5
numpy
pandas
```

MT5 must be running and logged in, unless terminal/login parameters are supplied separately.

## First run: enumerate the broker's BTC symbols

From the repository root:

```bat
scripts\btc_ml_v1\broker_audit\run_btc0_mt5_audit.bat
```

The script automatically selects a symbol only when exactly one tradeable BTC/XBT candidate is found. If there are multiple candidates, it writes them to:

```text
outputs/btc_ml_v1/btc0_broker_data_audit/broker_symbol_candidates.csv
```

Review that file, then run with the exact broker symbol, including suffixes or prefixes:

```bat
scripts\btc_ml_v1\broker_audit\run_btc0_mt5_audit.bat --symbol "BTCUSD#"
```

`BTCUSD#` above is only an example of command syntax. It is not assumed to be the user's broker symbol.

## Optional BTC-0 connection settings

BTC-0 uses its own optional names and does not read GML1 volume, symbol or execution settings:

```text
BTC0_MT5_TERMINAL_PATH
BTC0_MT5_LOGIN
BTC0_MT5_PASSWORD
BTC0_MT5_SERVER
BTC0_MT5_SYMBOL
```

Equivalent command-line options are also available:

```text
--terminal-path
--login
--password
--server
--symbol
--history-bars
--csv-root
--output-dir
```

Do not commit credentials or local output files.

## Output namespace

All default BTC-0 outputs are separate from GOLD:

```text
outputs/btc_ml_v1/btc0_broker_data_audit/
  btc0_broker_contract.json
  broker_symbol_candidates.csv
  history_depth.csv
  spread_distribution.csv
  observed_trading_hours_utc.csv
  existing_btc_csv_inventory.csv
```

### `btc0_broker_contract.json`

Records the audit controls, selected/requested symbol, masked account context, output manifest and warnings. It always declares that orders, signals, Discord and live readiness are off.

### `broker_symbol_candidates.csv`

Records exact broker symbol metadata and read-only current spread. Important fields include `trade_contract_size`, `volume_min`, `volume_step`, `digits`, `point`, `trade_stops_level` and `filling_mode`.

### `history_depth.csv`

Reports closed-row counts and first/last UTC timestamps for M1/M5/M15/H1/H4/D1. The current open MT5 bar is excluded.

### `spread_distribution.csv`

Reports M1 closed-bar spread percentiles in both broker points and price units, plus whether Saturday/Sunday bars were observed.

### `observed_trading_hours_utc.csv`

Reports only hours actually present in the sampled closed M1 history. It is an observation, not a guarantee of future broker hours.

### `existing_btc_csv_inventory.csv`

Reports BTC/XBT-named CSV paths, row counts, columns, first/last timestamp and duplicates. The latest CSV row is marked closed by the external CSV contract.

## Next stage boundary

BTC-1 CSV export and parity work must use the exact audited symbol and maintain asset-specific filenames. BTC candidate discovery remains independent and audit-only. No BTC live adapter, Discord notification or MT5 order path may be enabled until later explicit authorization and separate validation.
