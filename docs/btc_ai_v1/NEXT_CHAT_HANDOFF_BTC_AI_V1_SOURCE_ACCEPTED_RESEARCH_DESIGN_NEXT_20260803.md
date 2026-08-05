# NEXT CHAT HANDOFF — BTC AI V1 source accepted, fixed cost frozen, research design next

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-ai-v1-data-acquisition`
- date: `2026-08-03`
- status: `BTC_AI_V1_SOURCE_ACCEPTED_FIXED_COST_FROZEN_RESEARCH_DESIGN_NEXT`
- candidate discovery started: `false`

## Read order

1. `START_HERE_BTC_AI_V1.md`
2. `docs/btc_ai_v1/NEXT_CHAT_HANDOFF_BTC_AI_V1_SOURCE_ACCEPTED_RESEARCH_DESIGN_NEXT_20260803.md`
3. `config/btc_ai_v1/current_state_20260803.json`
4. `config/btc_ai_v1/next_action_20260803.json`
5. `docs/btc_ai_v1/BTC_AI_V1_SOURCE_ACCEPTANCE_AND_FIXED_COST_CONTRACT_20260803.md`
6. `config/btc_ai_v1/source_data_manifest_20260803.json`
7. `config/btc_ai_v1/fixed_cost_contract_20260803.json`
8. `config/btc_ai_v1/handoff_policy_20260803.json`
9. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md`

## Accepted source

`BTCUSD#`, XMTrading-MT5 3, MT5 broker-server time, closed bars only.

Period:

- M1: 2023-01-01 00:00 through 2026-08-03 03:02
- M5: through 2026-08-03 02:55
- M15: through 2026-08-03 02:45
- H1: through 2026-08-03 02:00
- H4: through 2026-08-02 20:00
- D1: through 2026-08-02 00:00

Use only files and SHA256 hashes in `source_data_manifest_20260803.json`. The earlier GOLD exports are not BTC inputs.

## Fixed cost

Primary contract:

`22.50 USD spread per BTC, once per completed 1.0-lot trade`

- LONG adjusted entry: raw M1 open + 22.50
- SHORT adjusted entry: raw M1 open - 22.50
- CSV variable spread: audit only
- economic-event spread expansion: not modeled
- commission/slippage/swap: zero under this contract

Do not change this after results. A change requires a new preregistered contract.

## Current next action

Create and freeze:

`BTC_AI_V1_01_RESEARCH_DESIGN_PREREGISTRATION`

It must define period splits, causal features, candidate generation, exact-M1 execution, gap rules, multiple-testing controls and formal gates before candidate outcomes are inspected.

## Continuous handoff rule

At every completed stage:

- create dated result Markdown and JSON;
- update current state and next action;
- create a dated NEXT_CHAT_HANDOFF;
- update the chronological history index;
- preserve contracts/results and use addenda for corrections;
- record branch, commits and input hashes.

## Prohibitions

- old BTC BCR is not restart authority;
- no GOLD writeback;
- no Discord or MT5 orders;
- no deployable/live-ready/final-signal claims;
- no candidate discovery before the design contract is frozen.
