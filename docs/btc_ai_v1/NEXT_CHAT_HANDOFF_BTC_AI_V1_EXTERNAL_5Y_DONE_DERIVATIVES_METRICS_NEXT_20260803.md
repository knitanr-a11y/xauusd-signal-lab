# NEXT CHAT HANDOFF — BTC AI V1 independent five-year history complete, derivatives metrics next

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-ai-v1-data-acquisition`
- date: `2026-08-03`
- status: `BTC_AI_V1_INDEPENDENT_2018_2022_HISTORY_EVALUATED_NO_SUPPORT_DERIVATIVES_METRICS_RESEARCH_NEXT`

## User direction

Do not wait several months for new prospective candles. Continue immediately with available independent historical and non-candle evidence while retaining strict preregistration and no-rescue rules.

## Completed immediately

### Binance USD-M perpetual futures

- official `BTCUSDT` monthly archives, 2020-01 through 2022-12
- 36 calendar months
- 1,578,240 exact M1 rows
- 100% calendar-minute coverage
- duplicate, reversal and gap count: 0
- 36 monthly funding archives available
- source ZIP checksums verified
- GitHub Actions run: `30786496193`

Frozen periods:

- fit: 2020, 12 months
- calibration: 2021H1, 6 months
- development: 2021H2, 6 months
- untouched final: 2022, 12 months

Forty-eight AI definitions tested using candle context versus volume/trade-count/taker-buy/funding features. Four passed development and two passed robustness.

Untouched 2022:

- `BEX_CANDLE_CONTEXT_SHORT_XGBR_P95`: 260 trades / 12 months = 21.67/month; PF 0.9850; net -536.84; positive months 4/12; FAIL.
- `BEX_MICRO_FUNDING_SHORT_XGB_P95`: 94 / 12 = 7.83/month; PF 1.1106; net +1,409.85; positive months 4/12; FAIL because 7/12 was preregistered.

No rescue or promotion.

### Binance spot

- official `BTCUSDT` monthly archives, 2018-01 through 2019-12
- 24 calendar months
- 1,045,460 M1 rows
- 16 exchange-gap intervals; never interpolated
- 68,875 complete M15 decisions with exact 720-minute M1 eligibility
- GitHub Actions run: `30787147478`

Frozen periods:

- fit: 2018H1, 6 months
- calibration: 2018H2, 6 months
- development: 2019H1, 6 months
- untouched final: 2019H2, 6 months

All 48 candidates failed development. Best PF was 0.7112. Robustness and 2019H2 were not opened.

## Formal result

- independent history added: 60 calendar months
- independent M1 rows: 2,623,700
- supported candidates: 0
- fixed spread remained 22.50 USD per BTC
- XM, Binance spot and Binance futures execution ledgers remained separate

## Required read order

1. `START_HERE_BTC_AI_V1.md`
2. this handoff
3. `config/btc_ai_v1/current_state_20260803.json`
4. `config/btc_ai_v1/next_action_20260803.json`
5. `config/btc_ai_v1/external_validation_result_20260803.json`
6. `config/btc_ai_v1/binance_external_validation_contract_20260803.json`
7. `docs/btc_ai_v1/BTC_AI_V1_BINANCE_FUTURES_EXTERNAL_VALIDATION_RESULT_20260803.md`
8. `config/btc_ai_v1/binance_spot_external_validation_contract_20260803.json`
9. `docs/btc_ai_v1/BTC_AI_V1_BINANCE_SPOT_EXTERNAL_VALIDATION_RESULT_20260803.md`
10. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md`

## Current next stage

`BTC_AI_V1_25_DERIVATIVES_METRICS_MARK_PREMIUM_OPEN_INTEREST_RESEARCH`

Proceed immediately with official causal derivatives-state sources:

1. Binance mark-price and premium-index archives.
2. Binance historical futures metrics if coverage and checksum audit pass.
3. Bybit open interest, funding and long-short-ratio replication.
4. Deribit BTC perpetual open-interest and funding replication.

Compare incremental value against the candle/volume baseline. Freeze source, periods, features, model registry and final gates before outcomes.

## Hard boundaries

- do not rescue `BEX_MICRO_FUNDING_SHORT_XGB_P95` despite positive aggregate 2022 net;
- do not relax positive-month gates;
- do not reuse venue outcomes for post-result threshold or side changes;
- keep each venue's execution price and cost ledger separate;
- no portfolio, Shadow, Discord, MT5 orders, live-ready or final signal;
- do not modify GOLD V19, Challenger C1, P75 or MOCHIPOYO.
