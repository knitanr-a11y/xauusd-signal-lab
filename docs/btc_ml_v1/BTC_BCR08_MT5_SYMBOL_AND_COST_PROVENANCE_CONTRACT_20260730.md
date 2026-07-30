# BTC BCR08 — MT5 symbol and cost provenance contract

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T19:20:00+09:00`
- status: `READ_ONLY_EVIDENCE_EXPORTER_READY`
- PnL evaluation: forbidden

## 1. Why BCR08 is mandatory

Track A has four frozen complete state machines and Track B has four frozen complete state machines. No profitability calculation is valid until the exact MT5 price-unit and cost interpretation is proven.

The historical BTC M15 CSV contains a `spread` column with values around the thousands. Treating those values as raw price, points, ticks or account-currency cost by assumption could change every result. BCR08 therefore captures the live terminal's exact symbol metadata before any shared value gate is written.

## 2. Frozen terminal provenance

Expected MT5 data path:

`C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675`

Frozen BTC M15 origin:

`C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv`

Frozen research snapshot SHA256:

`b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`

The live CSV may have grown after the frozen snapshot. BCR08 records the current SHA and row count but does not silently replace the frozen research snapshot.

## 3. Exact symbol hypothesis

The BAT tests the exact symbol name:

`BTCUSD#`

This is a hypothesis derived from the frozen `btcusdsharp_m15.csv` naming convention, not an authority claim. The exporter also records all `*BTC*` symbol candidates. If `BTCUSD#` is not found exactly, the run produces a blocked diagnostic ZIP rather than selecting a similar symbol.

No fuzzy symbol selection or first-match fallback is allowed.

## 4. Read-only MT5 boundary

Allowed MT5 API calls:

- `initialize` and `shutdown`;
- `terminal_info`;
- redacted `account_info`;
- `symbols_get`;
- `symbol_info`;
- `symbol_info_tick`.

Explicitly absent:

- `order_send` and `order_check`;
- `positions_get` and `orders_get`;
- `history_orders_get` and `history_deals_get`;
- `symbol_select`;
- any market-watch change;
- any order, position or account-history access.

The exporter first verifies that `terminal64.exe` is already running. It refuses to launch a closed terminal. After initialization it requires `terminal_info.data_path` to equal the frozen terminal data path exactly.

## 5. Privacy boundary

The account export may include only operational context such as broker server, account currency, leverage and margin mode.

It must not export:

- login/account number;
- account holder name;
- balance, equity, profit, free margin or liabilities;
- positions, orders, tickets or trade history.

## 6. Required symbol evidence

BCR08 records at least:

- exact symbol name, description and symbol path;
- `digits` and `point`;
- `spread` and `spread_float`;
- `trade_tick_size`;
- `trade_tick_value`, profit value and loss value;
- `trade_contract_size`;
- calculation, execution and trade modes;
- stop/freeze levels and filling/order modes;
- volume minimum, maximum and step;
- base, profit and margin currencies;
- one contemporaneous bid/ask tick when available.

Derived evidence includes:

- tick size in points;
- contemporaneous bid/ask spread in price and points;
- historical CSV spread quantiles multiplied by `point`, labeled as a conditional interpretation rather than accepted truth.

## 7. Commission remains separate

MT5 `symbol_info` does not prove the broker's commission schedule. BCR08 does not inspect historical deals to infer it.

Therefore a successful package has status:

`READY_MT5_SYMBOL_COST_PROVENANCE_COMMISSION_UNRESOLVED`

After package audit, commission must be resolved by an explicit broker/account contract or by a separately authorized sanitized evidence process. Zero commission must not be assumed merely because no commission field exists in `symbol_info`.

## 8. Output package

The one-run package contains:

1. read-me;
2. summary;
3. terminal information;
4. redacted account context;
5. BTC-like symbol candidates;
6. exact target symbol metadata;
7. tick snapshot;
8. current CSV spread observation;
9. cost-field interpretation;
10. runtime integrity;
11. file manifest;
12. error record.

The exporter creates the package whether it succeeds or blocks after startup. The operator uploads the first ZIP and does not rerun automatically.

## 9. Acceptance gate

BCR08 may pass only if:

- the already-running terminal is used;
- terminal data path matches the frozen Terminal ID;
- exact `BTCUSD#` exists, or ambiguity is explicitly resolved later without fallback;
- `digits`, positive `point`, positive tick size and positive contract size are present;
- profit currency is present;
- no forbidden API was called;
- account identity, balances and history were not exported;
- Collector, M7C and GOLD/MOCHIPOYO were unchanged.

Even after passing, `safe_to_compute_pnl` remains false until spread-column semantics and commission are formally frozen in the shared execution-cost contract.

## 10. Operator

- script: `scripts/btc_ml_v1/BCR08_mt5_symbol_cost_provenance/python/run_bcr08_mt5_symbol_cost_provenance.py`
- BAT: `scripts/btc_ml_v1/BCR08_mt5_symbol_cost_provenance/01_run_BCR08.bat`
- output: `%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\BCR08_mt5_symbol_cost_provenance\LATEST\99_UPLOAD_PACKAGE.zip`

Run exactly once after pulling the branch. Keep MT5, Collector and M7C running. Do not start or stop them for BCR08.
