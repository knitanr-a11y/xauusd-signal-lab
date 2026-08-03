# BTC AI V1 — OHLC State-Transition Reproducibility Manifest

Date: 2026-08-03  
Authority: accepted XM `BTCUSD#` closed-bar OHLC only

## Research package

Conversation artifact:

`BTC_AI_V1_OHLC_STATE_TRANSITION_RESEARCH_20260803.zip`

SHA256:

`0ed9eae486ca2bda53e48b6f19a254637ad31f3ebcbe84a4c9ab2c63e2bb462b`

The ZIP was expansion-tested and contains 23 files. It excludes all raw XM candles, GOLD files and external-market data.

## Included implementation components

- global OHLC state-transition preparation and model tasks
- global candidate aggregation and exact-M1 development evaluation
- phase-conditional expert model task and aggregation
- transition-conditional expert model task and aggregation
- candidate registries
- capability survivor tables
- full development grids
- Markdown and JSON formal results
- SHA256SUMS

Primary scripts:

1. `run_state_transition_research.py`
2. `prepare_state_data.py`
3. `run_state_model_task.py`
4. `aggregate_and_develop.py`
5. `run_phase_expert_task.py`
6. `aggregate_phase_experts.py`
7. `run_transition_expert_task.py`
8. `aggregate_transition_experts.py`

The scripts use the first-cycle exact-M1 helper implementations `stage02_capability.py` and `stage03_development_value.py`. Frozen GitHub contracts are authoritative over code comments.

## Formal GitHub contracts and results

- `config/btc_ai_v1/ohlc_state_transition_research_contract_20260803.json`
- `docs/btc_ai_v1/BTC_AI_V1_OHLC_STATE_TRANSITION_RESULT_20260803.md`
- `config/btc_ai_v1/ohlc_state_transition_result_20260803.json`
- `config/btc_ai_v1/ohlc_phase_conditional_expert_contract_20260803.json`
- `config/btc_ai_v1/ohlc_phase_expert_density_addendum_20260803.json`
- `docs/btc_ai_v1/BTC_AI_V1_OHLC_PHASE_EXPERT_RESULT_20260803.md`
- `config/btc_ai_v1/ohlc_phase_expert_result_20260803.json`
- `config/btc_ai_v1/ohlc_transition_conditional_expert_contract_20260803.json`
- `docs/btc_ai_v1/BTC_AI_V1_OHLC_TRANSITION_EXPERT_RESULT_20260803.md`
- `config/btc_ai_v1/ohlc_transition_expert_result_20260803.json`

## Reproduction boundary

- M15 closed decisions
- exact next M1 open and exact M1 path
- fixed spread 22.50 USD per BTC
- SL first on a same-M1 collision
- one-position non-overlap
- no external or volume data
- development 2024-01 through 2025-12, exactly 24 calendar months
- 2026 not opened in these cycles

Formal supported candidates: **0**.
