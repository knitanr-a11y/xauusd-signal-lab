# BTC BCR08A — KIWAMI commission contract resolution

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T19:35:00+09:00`
- status: `KIWAMI_COMMISSION_ZERO_CONTRACT_FROZEN`
- historical PnL opened: no

## 1. Exact account/symbol evidence

BCR08 established:

- terminal: `XMTrading MT5`
- company: `Tradexfin Limited`
- server: `XMTrading-MT5 3`
- exact symbol: `BTCUSD#`
- symbol tree path: `Cryptocurrencies\\KIWAMI\\BTCUSD#`
- account base currency: `JPY`

The KIWAMI path is not inferred from the uploaded CSV filename alone; it is the exact path returned by the connected MT5 terminal for the target symbol.

## 2. Broker contract evidence

The official XMTrading KIWAMI account page and trading-fees page state that KIWAMI accounts have no per-trade commission. The KIWAMI account page includes cryptocurrency derivatives among the supported markets.

Official sources inspected on 2026-07-30:

- `https://www.xmtrading.com/jp/account-types/kiwami`
- `https://www.xmtrading.com/jp/trading-fees`

## 3. Frozen commission interpretation

For `BTCUSD#` under the exact `Cryptocurrencies\\KIWAMI` account contract:

- entry commission: `0`
- exit commission: `0`
- round-trip commission: `0`

The economic transaction cost is therefore carried by spread, slippage and any applicable financing/swap, not a separate commission charge.

## 4. Scope and caution

This contract applies only to the exact XMTrading KIWAMI symbol/account context evidenced by BCR08. It must not be reused for:

- XM Zero accounts;
- another broker;
- a symbol outside the KIWAMI tree;
- a future broker contract after terms change.

The source pages were current at the inspection date. The retrospective evaluator records the contract date and must not represent it as an independently archived historical tariff for every prior day. To protect against that limitation, the shared value gate reports spread-only base results and fixed adverse-cost stress scenarios without changing formulas.

## 5. Remaining cost issue

Commission is resolved. Swap/rollover remains separate because the symbol snapshot contains non-zero swap metadata and exact historical financing charges were not reconstructed from deal history.

The value gate may proceed only under a contract that clearly separates:

1. all-episode spread-and-commission results;
2. no-rollover full-known-cost episodes;
3. rollover-exposed episodes whose financing remains provisional;
4. deterministic adverse execution stress results.

## 6. Decision

Commission is frozen at zero for this exact KIWAMI context. This does not yet promote any Track A or Track B machine.