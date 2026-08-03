# START HERE — BTC AI Candidate Research V1

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-ai-v1-data-acquisition`
- status: `BTC_AI_V1_SOURCE_ACCEPTED_FIXED_COST_FROZEN_RESEARCH_DESIGN_NEXT`
- updated: `2026-08-03`

## Scope

BTCを、GOLDで採用したAI研究方式を参考にしつつ、BTC専用のデータ・コスト・評価契約でゼロベース研究する。

旧BTC BCR、旧stacking、旧5候補は新研究のauthorityにしない。必要な場合のみ重複回避用のaudit historyとして扱う。

## Unique latest handoff

`docs/btc_ai_v1/NEXT_CHAT_HANDOFF_BTC_AI_V1_SOURCE_ACCEPTED_RESEARCH_DESIGN_NEXT_20260803.md`

## Required read order

1. `START_HERE_BTC_AI_V1.md`
2. latest handoff above
3. `config/btc_ai_v1/current_state_20260803.json`
4. `config/btc_ai_v1/next_action_20260803.json`
5. `docs/btc_ai_v1/BTC_AI_V1_SOURCE_ACCEPTANCE_AND_FIXED_COST_CONTRACT_20260803.md`
6. `config/btc_ai_v1/source_data_manifest_20260803.json`
7. `config/btc_ai_v1/fixed_cost_contract_20260803.json`
8. `config/btc_ai_v1/handoff_policy_20260803.json`
9. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md`

Do not search old handoffs or other branches before completing this order.

## Current state

- BTCUSD# six-timeframe source snapshot accepted.
- GOLD contamination audit passed.
- M1 through D1 cross-timeframe reconstruction passed exactly.
- fixed spread cost frozen at 22.50 USD per BTC once per completed 1.0-lot trade.
- candidate discovery has not started.

## Next stage

`BTC_AI_V1_01_RESEARCH_DESIGN_PREREGISTRATION`

Freeze the full research and evaluation design before candidate outcomes are inspected.

## Hard boundaries

- MT5 broker-server time only; no JST conversion.
- closed bars only.
- no interpolation or fabricated M1 bars.
- no variable spread or economic-event expansion in the primary result.
- no candidate discovery before design freeze.
- no GOLD V19, Challenger C1 or P75 modification.
- no Discord, MT5 order, live-ready or final signal.
- every stage must leave dated result and next-chat handoff history.
