# START HERE — BTC AI Candidate Research V1

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-ai-v1-data-acquisition`
- status: `BTC_AI_V1_OHLC_STATE_TRANSITION_LOCAL_EDGES_FOUND_NO_SUPPORTED_CANDIDATE`
- updated: `2026-08-03`

## Scope and source authority

BTC専用のデータ・コスト・評価契約でゼロベース研究する。旧BTC BCR、旧stacking、旧5候補はauthorityにしない。GOLD V19、Challenger C1、P75、MOCHIPOYOを変更しない。

唯一の正本データは、受領・監査済みのXM `BTCUSD#` closed-bar snapshot:

- M1 / M5 / M15 / H1 / H4 / D1
- MT5 broker-server time
- fixed spread: 22.50 USD per completed 1 BTC trade
- closed M15 decision and exact M1 execution

外部市場データはユーザーにより拒否された。関連workflow、契約、結果、handoff、取得コードは現在のbranchから削除済みで、Git履歴の事故監査以外には使用しない。volume、funding、open-interest、order-flowも使用しない。

## Unique latest handoff

`docs/btc_ai_v1/NEXT_CHAT_HANDOFF_BTC_AI_V1_OHLC_STATE_TRANSITION_LOCAL_EDGES_NO_SUPPORT_NEXT_20260803.md`

## Required read order

1. `START_HERE_BTC_AI_V1.md`
2. latest handoff above
3. `docs/btc_ai_v1/USER_SCOPE_CORRECTION_EXTERNAL_DATA_REJECTED_OHLC_AUTHORITY_20260803.md`
4. `docs/btc_ai_v1/BTC_AI_V1_OHLC_2026_FAILURE_ROOT_CAUSE_FORENSIC_20260803.md`
5. `config/btc_ai_v1/ohlc_2026_failure_root_cause_20260803.json`
6. `config/btc_ai_v1/ohlc_state_transition_research_contract_20260803.json`
7. `docs/btc_ai_v1/BTC_AI_V1_OHLC_STATE_TRANSITION_RESULT_20260803.md`
8. `config/btc_ai_v1/ohlc_state_transition_result_20260803.json`
9. `config/btc_ai_v1/ohlc_phase_conditional_expert_contract_20260803.json`
10. `config/btc_ai_v1/ohlc_phase_expert_density_addendum_20260803.json`
11. `docs/btc_ai_v1/BTC_AI_V1_OHLC_PHASE_EXPERT_RESULT_20260803.md`
12. `config/btc_ai_v1/ohlc_phase_expert_result_20260803.json`
13. `config/btc_ai_v1/ohlc_transition_conditional_expert_contract_20260803.json`
14. `docs/btc_ai_v1/BTC_AI_V1_OHLC_TRANSITION_EXPERT_RESULT_20260803.md`
15. `config/btc_ai_v1/ohlc_transition_expert_result_20260803.json`
16. `docs/btc_ai_v1/BTC_AI_V1_OHLC_STATE_TRANSITION_REPRODUCIBILITY_MANIFEST_20260803.md`
17. `config/btc_ai_v1/current_state_20260803.json`
18. `config/btc_ai_v1/next_action_20260803.json`
19. `config/btc_ai_v1/source_data_manifest_20260803.json`
20. `config/btc_ai_v1/fixed_cost_contract_20260803.json`
21. `config/btc_ai_v1/frequency_reporting_contract_20260803.json`
22. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md`

Do not search old handoffs or deleted external-data paths before completing this order.

## Root cause already established

The 2024–2025 winners failed in 2026 because the same high-score OHLC pattern changed from an early bearish impulse/correction into a mature and extended selloff. Generic SHORT opportunity remained, but score ordering collapsed and stop-first outcomes increased.

Formal root cause:

`OHLC_STATE_TRANSITION_AND_CONDITIONAL_MEANING_SHIFT_CAUSED_LATE_SHORT_SELECTION`

## Completed OHLC state-transition research

All new cycles used exactly 24 development months, 2024-01 through 2025-12. The consumed 2026 seven-month period was not opened.

### Global state-feature model

- 48 candidates / 384 exact-M1 configurations
- positive net: 72
- PF >= 1.15: 0
- maximum PF: 1.1302
- formal survivors: 0

### Phase-conditional experts

- 48 raw / 42 capability survivors / 336 configurations
- PF >= 1.20: 32
- formal survivors: 0
- `EARLY_IMPULSE LONG`: 64 trades / 24 months = 2.67/month, PF 1.4538, rejected for insufficient density
- `RANGE_NEUTRAL LONG`: 268 / 24 = 11.17/month, PF 1.3704, rejected for transition concentration

### Transition-conditional experts

- 48 raw / 26 capability survivors / 208 configurations
- PF >= 1.20: 30
- formal survivors: 0
- `INTO_EARLY_IMPULSE LONG`: 78 / 24 = 3.25/month, PF 1.6162, rejected for density and D1-regime transfer
- `EXHAUSTION_TO_REVERSAL SHORT`: 79 / 24 = 3.29/month, PF 1.4931, rejected for density and time persistence

Formal supported candidates remain **0**. The high-PF local patterns are hypotheses only and may not be combined, rescued or evaluated on 2026.

## Current next stage

`BTC_AI_V1_OHLC_SEQUENCE_TRANSITION_HAZARD_MULTITASK_PREREGISTRATION`

Use OHLC sequences rather than a single-row score. Include every preregistered phase and transition, compare a small TCN/GRU with a non-neural sequence baseline, and require leave-one-D1-regime-out and leave-one-transition-type-out transfer before PnL shortlisting.

## Hard boundaries

- XM BTCUSD# OHLC only; no external or volume data.
- MT5 broker-server time; no JST conversion.
- closed bars only; exact M1 execution and no fabricated bars.
- fixed spread 22.50 USD.
- every count includes exact calendar months and monthly distribution.
- no local-winner combination or minimum-count relaxation.
- no use of 2026 for selection or support.
- no portfolio, Shadow, Discord, MT5 orders, live-ready or final signal.
- every stage must leave dated contracts, results, current state, next action and next-chat handoff.
