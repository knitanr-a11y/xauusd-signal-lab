# START HERE — BTC AI Candidate Research V1

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-ai-v1-data-acquisition`
- status: `BTC_AI_V1_INDEPENDENT_2018_2022_HISTORY_EVALUATED_NO_SUPPORT_DERIVATIVES_METRICS_RESEARCH_NEXT`
- updated: `2026-08-03`

## Scope

BTCをBTC専用のデータ・コスト・評価契約でゼロベース研究する。旧BTC BCR、旧stacking、旧5候補はauthorityにしない。GOLD V19、Challenger C1、P75、MOCHIPOYOを変更しない。

ユーザーの明示指示により、数カ月の新規データ待ちは研究方針にしない。現在利用できる独立履歴と因果的な非ローソク足データで直ちに継続する。

## Unique latest handoff

`docs/btc_ai_v1/NEXT_CHAT_HANDOFF_BTC_AI_V1_EXTERNAL_5Y_DONE_DERIVATIVES_METRICS_NEXT_20260803.md`

## Required read order

1. `START_HERE_BTC_AI_V1.md`
2. latest handoff above
3. `config/btc_ai_v1/current_state_20260803.json`
4. `config/btc_ai_v1/next_action_20260803.json`
5. `config/btc_ai_v1/external_validation_result_20260803.json`
6. `config/btc_ai_v1/binance_external_validation_contract_20260803.json`
7. `docs/btc_ai_v1/BTC_AI_V1_BINANCE_FUTURES_EXTERNAL_VALIDATION_RESULT_20260803.md`
8. `config/btc_ai_v1/binance_spot_external_validation_contract_20260803.json`
9. `docs/btc_ai_v1/BTC_AI_V1_BINANCE_SPOT_EXTERNAL_VALIDATION_RESULT_20260803.md`
10. `config/btc_ai_v1/source_data_manifest_20260803.json`
11. `config/btc_ai_v1/fixed_cost_contract_20260803.json`
12. `config/btc_ai_v1/frequency_reporting_contract_20260803.json`
13. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md`

Do not search old handoffs or other branches before completing this order.

## Current formal evidence

### XM BTCUSD# 2023–2026

- deterministic rules, binary ML, diverse classifiers, direct-payoff regression and pairwise ranking were tested.
- the seven-month 2026 untouched period was consumed.
- supported candidates: 0.
- further same-history candle-only multiplication is frozen.

### Binance USD-M perpetual 2020–2022

- 36 months, 1,578,240 exact M1 rows, 100% minute coverage.
- volume, trade count, taker-buy ratio and funding were included.
- four development survivors, two robustness survivors.
- untouched 2022: supported candidates 0.
- one candidate had PF 1.1106 and +1,409.85 over 12 months but only 4 positive months versus the frozen requirement of 7; it remains rejected.

### Binance spot 2018–2019

- 24 months, 1,045,460 M1 rows.
- exchange gaps were not filled; exact-M1 continuity was required.
- all 48 candidates failed the six-month 2019H1 development gate.
- best PF: 0.7112.
- 2019H2 remained unopened.

Combined independent evidence acquired immediately:

- 60 calendar months
- 2,623,700 M1 rows
- official monthly archives and checksums
- supported candidates: **0**

## Current next stage

`BTC_AI_V1_25_DERIVATIVES_METRICS_MARK_PREMIUM_OPEN_INTEREST_RESEARCH`

Do not wait for months of new candles. Acquire and audit mark price, premium index, historical metrics, open interest, funding and long-short ratios from official Binance, Bybit and Deribit sources. Compare their incremental value against the frozen candle/volume baseline under new preregistered period and model contracts.

## Hard boundaries

- fixed spread remains 22.50 USD per completed 1 BTC trade unless a new user-authorized contract is created.
- every count must include exact calendar months and monthly distribution.
- keep XM, Binance spot, Binance futures, Bybit and Deribit execution ledgers separate.
- do not rescue near-positive rejected candidates.
- no post-result threshold, direction, month, feature, target, model, exit or horizon rescue.
- no portfolio, Shadow, Discord, MT5 orders, live-ready or final signal.
- every stage must leave dated results, current state, next action and next-chat handoff.
