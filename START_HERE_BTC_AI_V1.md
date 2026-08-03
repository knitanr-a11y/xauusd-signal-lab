# START HERE — BTC AI Candidate Research V1

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-ai-v1-data-acquisition`
- status: `BTC_AI_V1_RESEARCH_DESIGN_FROZEN_PIPELINE_IMPLEMENTATION_NEXT`
- updated: `2026-08-03`

## Scope

BTCを、GOLDで採用したAI研究方式の方法論を参考にしつつ、BTC専用のデータ・コスト・評価契約でゼロベース研究する。

旧BTC BCR、旧stacking、旧5候補は新研究のauthorityにしない。必要な場合のみ重複回避用のaudit historyとして扱う。

## Unique latest handoff

`docs/btc_ai_v1/NEXT_CHAT_HANDOFF_BTC_AI_V1_DESIGN_FROZEN_PIPELINE_IMPLEMENTATION_NEXT_20260803.md`

## Required read order

1. `START_HERE_BTC_AI_V1.md`
2. latest handoff above
3. `config/btc_ai_v1/current_state_20260803.json`
4. `config/btc_ai_v1/next_action_20260803.json`
5. `config/btc_ai_v1/source_data_manifest_20260803.json`
6. `config/btc_ai_v1/fixed_cost_contract_20260803.json`
7. `config/btc_ai_v1/research_design_contract_20260803.json`
8. `docs/btc_ai_v1/BTC_AI_V1_RESEARCH_DESIGN_PREREGISTRATION_20260803.md`
9. `config/btc_ai_v1/handoff_policy_20260803.json`
10. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md`

Do not search old handoffs or other branches before completing this order.

## Current state

- BTCUSD# six-timeframe source snapshot accepted and hash-frozen.
- GOLD contamination audit passed.
- M1 through D1 cross-timeframe reconstruction passed exactly.
- fixed spread cost frozen at 22.50 USD per BTC once per completed 1.0-lot trade.
- research design preregistration is frozen.
- candidate outcomes have not been inspected.
- the 2026-01-01 through 2026-07-31 final test is unopened.

## Current next stage

`BTC_AI_V1_02_CAUSAL_FEATURE_AND_CANDIDATE_REGISTRY_IMPLEMENTATION`

Implement causal features, expanding-fold masks, deterministic candidate registry, outcome-blind capability gates and exact-M1 replay primitives. Development outcomes may be opened only after implementation verification. The 2026 final test remains locked until the finalist list is frozen.

## Hard boundaries

- MT5 broker-server time only; no JST conversion.
- closed bars only.
- M15 decision grid and exact M1 execution.
- no interpolation or fabricated M1 bars.
- primary spread is fixed 22.50 USD; CSV variable spread is audit-only.
- no economic-event spread model.
- no old BTC candidate seeding.
- no final-test inspection before finalist freeze.
- no post-result threshold, direction, session, exit or horizon rescue.
- no GOLD V19, Challenger C1 or P75 modification.
- no Discord, MT5 order, live-ready or final signal.
- every stage must leave dated result and next-chat handoff history.
