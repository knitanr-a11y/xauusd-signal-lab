# BTC BCR08 — MT5 symbol and cost provenance result

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T19:30:00+09:00`
- status: `BCR08_ACCEPTED_SYMBOL_SPREAD_PROVENANCE_COMMISSION_CONTRACT_SEPARATE`
- PnL evaluation performed: no

## 1. Submitted package

- uploaded package: `99_UPLOAD_PACKAGE(103).zip`
- package SHA256: `2b5df4bcdf0f2c07c0d246a3cfe057f05ef4751f7ab3e3c71e8f993cd24cbbf7`
- members: `12 / 12`
- duplicate or unsafe ZIP members: `0`
- manifest hash/byte mismatches: `0`
- exporter status: `READY_MT5_SYMBOL_COST_PROVENANCE_COMMISSION_UNRESOLVED`
- exporter error: `null`

## 2. Runtime and privacy gate

The exporter used an already-running XMTrading MT5 terminal.

- terminal data path exact match: true
- terminal: `XMTrading MT5`
- company: `Tradexfin Limited`
- server: `XMTrading-MT5 3`
- account currency: `JPY`
- order send/check: not used
- positions/orders/history: not queried
- `symbol_select`: not called
- Collector/M7C/GOLD/MOCHIPOYO modification: false
- account number, name, balance, equity and profit exported: false

The runtime integrity gate passes.

## 3. Exact BTC symbol

The hypothesis `BTCUSD#` was found exactly without fuzzy fallback.

- name: `BTCUSD#`
- path: `Cryptocurrencies\\KIWAMI\\BTCUSD#`
- description: `Bitcoin vs US Dollar`
- chart mode: `0` (`BID` bars under the MQL5 enum)
- digits: `2`
- point: `0.01`
- trade tick size: `0.01`
- tick size in points: `1`
- contract size: `1.0`
- calculation mode: `4`
- base/profit/margin currency: `USD / USD / USD`
- minimum lot / step: `0.01 / 0.01`

For one lot, a USD 1.00 BTC price movement corresponds to USD 1.00 before account-currency conversion. The later value gate reports USD profit-currency results and does not invent a historical USDJPY conversion series.

## 4. Spread semantics

At capture time:

- symbol-info spread: `2250` points
- bid: `64561.6`
- ask: `64584.1`
- bid/ask price difference: `22.5`
- `(ask - bid) / point`: `2250`
- live CSV latest spread field: `2250`

The live CSV spread distribution was:

- minimum/median/latest: `2250`
- q90/q99/maximum: `3000`

The frozen research snapshot has the same spread support (`2250` and `3000`). The consistent interpretation is therefore:

`spread_price = CSV spread × point`

Thus the historical spread levels are USD `22.50` and USD `30.00` per one BTC contract, not USD 2250/3000.

## 5. Live CSV versus frozen snapshot

The live source file had continued to grow:

- live rows: `30,687`
- live latest server open: `2026-07-30 12:45:00`
- live SHA256: `7d245b0d38723c7546f6c50fbad28f169ff161f88e35a45562bfed4c39d24e19`

The frozen research snapshot remains:

- rows: `30,661`
- SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`

The live file does not replace or extend the frozen retrospective input.

## 6. Commission and financing boundary

The MT5 package alone did not expose a commission schedule and did not query deal history. Commission is resolved separately by an exact account-type contract record.

The symbol snapshot contains non-zero swap metadata. Therefore swap/rollover must not be silently assumed zero. A shared value gate must distinguish:

- spread-and-commission net results;
- no-rollover episodes;
- rollover-exposed episodes;
- any later fully specified financing model.

## 7. Decision

BCR08 passes for exact symbol, bar side, point/tick/contract and spread-unit provenance.

It does not by itself authorize a profitability claim. The next stage must freeze a common execution/cost contract before opening any Track A or Track B future-return result.