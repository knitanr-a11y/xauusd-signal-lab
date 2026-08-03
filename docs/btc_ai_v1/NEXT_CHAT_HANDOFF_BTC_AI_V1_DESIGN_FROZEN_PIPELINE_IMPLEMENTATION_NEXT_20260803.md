# NEXT CHAT HANDOFF — BTC AI V1 design frozen, causal pipeline implementation next

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-ai-v1-data-acquisition`
- date: `2026-08-03`
- status: `BTC_AI_V1_RESEARCH_DESIGN_FROZEN_PIPELINE_IMPLEMENTATION_NEXT`
- completed stage: `BTC_AI_V1_01_RESEARCH_DESIGN_PREREGISTRATION`
- candidate outcomes inspected: `false`
- untouched final test opened: `false`

## Required read order

1. `START_HERE_BTC_AI_V1.md`
2. this handoff
3. `config/btc_ai_v1/current_state_20260803.json`
4. `config/btc_ai_v1/next_action_20260803.json`
5. `config/btc_ai_v1/source_data_manifest_20260803.json`
6. `config/btc_ai_v1/fixed_cost_contract_20260803.json`
7. `config/btc_ai_v1/research_design_contract_20260803.json`
8. `docs/btc_ai_v1/BTC_AI_V1_RESEARCH_DESIGN_PREREGISTRATION_20260803.md`
9. `config/btc_ai_v1/handoff_policy_20260803.json`
10. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md`

## Frozen input and cost

- symbol: `BTCUSD#`
- source: accepted six-timeframe 2023-01-01 through 2026-08-03 snapshot
- time: MT5 broker-server naive
- spread: fixed `22.50 USD` per BTC once per completed 1.0-lot trade
- variable CSV spread: audit only
- economic-event spread expansion: not modeled
- no interpolation or fabricated bars

## Frozen development design

M15 is the decision grid; exact M1 is execution. M5/H1/H4/D1 are causal context only.

Development validation folds:

- 2024H1
- 2024H2
- 2025H1
- 2025H2

Each fold uses expanding prior history for fitting/calibration.

Untouched final test:

`2026-01-01 <= decision_time < 2026-08-01`

Do not calculate, inspect or summarize candidate PnL from the final-test interval before the finalist registry is frozen.

## Candidate search limits

- six predefined candidate families;
- maximum 1,200 raw candidates and 200 per family;
- maximum 300 outcome-blind capability survivors;
- maximum 20 development shortlist candidates;
- maximum 5 final-test candidates.

All candidate configurations and outcomes must be retained.

## Next stage

`BTC_AI_V1_02_CAUSAL_FEATURE_AND_CANDIDATE_REGISTRY_IMPLEMENTATION`

Implement:

- causal multi-timeframe feature builder;
- expanding-fold masks;
- deterministic candidate registry;
- outcome-blind density/diversity gate;
- exact-M1 replay primitives with fixed spread, SL-first collision and gap invalidation;
- tests proving no final-test outcome access.

Development PnL may be opened only after implementation verification. The 2026 final test remains locked.

## No-rescue and safety

- no old BTC candidate seeding;
- no cost, period, threshold, direction or exit change after results;
- no post-result month/session deletion;
- no portfolio construction before individual results freeze;
- no GOLD changes;
- no Discord, MT5 orders, live-ready or final signal;
- no retrospective classification can automatically authorize Shadow.

## Continuous history requirement

After every stage, create dated Markdown and JSON results, update state/next action, update the history index and create a new dated handoff. Never overwrite a frozen contract; use a dated addendum for corrections.
