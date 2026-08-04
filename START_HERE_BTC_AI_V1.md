# START HERE — BTC AI Candidate Research V1

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative archive/runtime branch: `feature/btc-ai-v1-data-acquisition`
- current status: `BTC_AI_V1_STAGE55_ACTIVE_OBSERVATION_CONTINUES_SIMPLE_RULE_ANTI_OVERFIT_PREREGISTRATION_NEXT`
- updated: `2026-08-04`

## Read first

1. `docs/btc_ai_v1/NEXT_CHAT_HANDOFF_BTC_AI_V1_STAGE55_ACTIVE_SIMPLE_RULE_ANTI_OVERFIT_PREREGISTRATION_NEXT_20260804.md`
2. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX_V2_20260804.md`
3. `docs/btc_ai_v1/BTC_AI_V1_CUMULATIVE_RESEARCH_RECORD_THROUGH_STAGE55_AND_SIMPLE_RULE_NEXT_20260804.md`
4. `docs/btc_ai_v1/BTC_AI_V1_SIMPLE_RULE_ANTI_OVERFIT_RESEARCH_DESIGN_20260804.md`
5. `config/btc_ai_v1/simple_rule_anti_overfit_research_contract_20260804.json`
6. `config/btc_ai_v1/current_state_stage55_20260804.json`
7. `config/btc_ai_v1/next_action_simple_discretionary_rules_20260804.json`
8. `docs/btc_ai_v1/BTC_AI_V1_STAGE55_DUAL_REVERSE_SHORT_PROSPECTIVE_SHADOW_20260804.md`
9. `config/btc_ai_v1/stage55_dual_reverse_short_shadow_contract_20260804.json`

Read all nine from beginning to end before implementation or outcome calculation.

## Authority

Use only accepted XM `BTCUSD#` closed-bar OHLC:

- M1/M5/M15/H1/H4/D1
- MT5 broker-server naive time
- closed-bar decisions and exact-M1 execution
- missing exact entry M1 means invalid candidate; no fallback
- same-M1 TP/SL collision is SL first
- fixed spread 22.50 USD per completed 1 BTC trade
- no external-market, funding, open-interest, order-flow, tick-volume or real-volume features

Old BTC BCR, stacking and frozen candidates are not authority for this BTC AI V1 line. Do not modify GOLD V19, Challenger C1, P75 or MOCHIPOYO.

## Stage55 frozen prospective Shadow

Two post-selection diagnostic reverse-SHORT families are running observation-only on the user PC.

- activation status: `READY_NO_BACKFILL_ACTIVATED`
- activation cutoff: `2026-08-04 10:52:00` MT5
- accepted candidates at activation: 0
- runtime state: `%LOCALAPPDATA%/xauusd_signal_lab/btc_stage55_shadow`
- minimum conclusion gate per family: 20 closed trades and 6 calendar months

Do not change model, Q70, confirmation, stop, target, hold, family membership, activation cutoff or no-backfill state.

Discord is accepted-entry delivery only and must not affect research selection. MT5 orders, live trading, live-ready and final signal remain OFF.

## Research history

Current top-level index:

`docs/btc_ai_v1/RESEARCH_HISTORY_INDEX_V2_20260804.md`

Detailed layers:

- Stages00–30: `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md`
- Stages31–36: `docs/btc_ai_v1/RESEARCH_HISTORY_STAGE31_36_ADDENDUM_20260804.md`
- Stages37–55 and synthesis: `docs/btc_ai_v1/BTC_AI_V1_CUMULATIVE_RESEARCH_RECORD_THROUGH_STAGE55_AND_SIMPLE_RULE_NEXT_20260804.md`

Key retained research asset outside Stage55:

- low-frequency ATR shock second-rejection LONG specialist

Key promotion stops:

- Stage37 deterministic midpoint failure failed 2026 diagnosis
- Stage38/39 meta LONG/SHORT/stack failed 2026 diagnosis
- 2h/4h/6h interaction policies failed 2026 diagnosis
- candidates that only rebounded in consumed 2026 are not restored

## Next independent cycle

The immediate next task is preregistration, not backtesting.

Research at most four simple, human-readable deterministic rule families on a separate branch and separate clone.

Proposed branch:

`feature/btc-simple-discretionary-rule-research`

Proposed clone:

`C:\xauusd-signal-lab-btc-simple-rules`

Limits:

- maximum four families
- one designated base rule per family
- maximum two robustness neighbors per family
- maximum twelve configurations total
- no ML in the first pass
- neighbors are stress tests and cannot replace a failing base
- exact rules and numerical gates must be approved and frozen before PnL/PF/win-rate is opened

Because historical 2023–2026-07 OHLC has been heavily consumed, new historical results are retrospective exploratory evidence. Fresh no-backfill prospective evidence is required before promotion.
