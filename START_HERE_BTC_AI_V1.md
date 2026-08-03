# START HERE — BTC AI Candidate Research V1

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-ai-v1-data-acquisition`
- status: `BTC_AI_V1_OHLC_SEQUENCE_INFORMATION_FOUND_NO_STABLE_PAYOFF_ORDERING`
- updated: `2026-08-03`

## Scope and source authority

BTCをBTC専用のデータ・コスト・評価契約でゼロベース研究する。旧BTC BCR、旧stacking、旧5候補はauthorityにしない。GOLD V19、Challenger C1、P75、MOCHIPOYOを変更しない。

唯一の正本データは、受領・監査済みのXM `BTCUSD#` closed-bar OHLC snapshot:

- M1 / M5 / M15 / H1 / H4 / D1
- MT5 broker-server time
- fixed spread: 22.50 USD per completed 1 BTC trade
- closed M15 decision and exact M1 execution

外部市場データはユーザーにより拒否された。関連workflow、契約、結果、handoff、取得コードは現在のbranchから削除済みで、Git履歴の事故監査以外には使用しない。volume、funding、open-interest、order-flowも使用しない。

## Unique latest handoff

`docs/btc_ai_v1/NEXT_CHAT_HANDOFF_BTC_AI_V1_OHLC_SEQUENCE_NO_SUPPORT_EVENT_ANCHOR_NEXT_20260803.md`

## Required read order

1. `START_HERE_BTC_AI_V1.md`
2. latest handoff above
3. `docs/btc_ai_v1/USER_SCOPE_CORRECTION_EXTERNAL_DATA_REJECTED_OHLC_AUTHORITY_20260803.md`
4. `docs/btc_ai_v1/BTC_AI_V1_OHLC_2026_FAILURE_ROOT_CAUSE_FORENSIC_20260803.md`
5. `config/btc_ai_v1/ohlc_2026_failure_root_cause_20260803.json`
6. `config/btc_ai_v1/ohlc_state_transition_research_contract_20260803.json`
7. `docs/btc_ai_v1/BTC_AI_V1_OHLC_STATE_TRANSITION_RESULT_20260803.md`
8. `docs/btc_ai_v1/BTC_AI_V1_OHLC_PHASE_EXPERT_RESULT_20260803.md`
9. `docs/btc_ai_v1/BTC_AI_V1_OHLC_TRANSITION_EXPERT_RESULT_20260803.md`
10. `config/btc_ai_v1/ohlc_sequence_transition_hazard_multitask_contract_20260803.json`
11. `docs/btc_ai_v1/BTC_AI_V1_OHLC_SEQUENCE_MULTITASK_RESULT_20260803.md`
12. `config/btc_ai_v1/ohlc_sequence_multitask_result_20260803.json`
13. `docs/btc_ai_v1/BTC_AI_V1_OHLC_SEQUENCE_MULTITASK_REPRODUCIBILITY_MANIFEST_20260803.md`
14. `config/btc_ai_v1/current_state_20260803.json`
15. `config/btc_ai_v1/next_action_20260803.json`
16. `config/btc_ai_v1/source_data_manifest_20260803.json`
17. `config/btc_ai_v1/fixed_cost_contract_20260803.json`
18. `config/btc_ai_v1/frequency_reporting_contract_20260803.json`
19. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md`

Do not search old handoffs or deleted external-data paths before completing this order.

## Root cause already established

The 2024–2025 winners failed in 2026 because the same high-score OHLC pattern changed from an early bearish impulse/correction into a mature and extended selloff. Generic SHORT opportunity remained, but score ordering collapsed and stop-first outcomes increased.

Formal root cause:

`OHLC_STATE_TRANSITION_AND_CONDITIONAL_MEANING_SHIFT_CAUSED_LATE_SHORT_SELECTION`

## Previous state-transition cycles

All previous cycles used exactly 24 development months, 2024-01 through 2025-12. The consumed 2026 seven-month period was not opened.

- global state-feature model: maximum PF 1.1302; formal survivors 0
- phase experts: maximum PF 1.4538; failed density/transfer; formal survivors 0
- transition experts: maximum PF 1.6162; failed density/time/regime transfer; formal survivors 0

Local high-PF patterns remain hypotheses only and may not be combined or rescued.

## Completed OHLC sequence multi-task research

Each decision used 64 consecutive closed M15 bars, equal to 16 hours, plus the latest fully closed H1/H4/D1 OHLC context.

Targets:

- first named transition within the next 16 M15 bars
- LONG/SHORT MFE and MAE over 480 exact M1 bars
- LONG/SHORT fixed-policy payoff using 1 ATR stop, 2 ATR target and 480-minute hold

Compared models:

- LightGBM lag/summary sequence baseline
- shared small GRU multi-task model

Results over exactly 24 calendar months:

- valid continuous sequence rows: 100,948
- raw candidates: 32
- outcome-blind capability survivors: 32
- candidate events: 250–1,156 over 24 months = 10.42–48.17/month
- exact-M1 configurations: 256
- positive-net configurations: 88
- PF >= 1.20 configurations: 0
- provisional survivors: 0
- transfer, robustness and 2026 diagnosis: not opened

Strongest LightGBM configuration:

- 580 completed trades / 24 months = 24.17/month
- monthly min / median / max: 4 / 23.5 / 60
- PF 1.1539
- net +21,262.16
- positive months 13/24
- positive half-years 3/4
- rejected for PF and monthly-persistence gates

Strongest GRU configuration:

- 363 / 24 months = 15.13/month
- monthly min / median / max: 4 / 15.5 / 30
- PF 1.1496
- net +13,276.96
- positive months 13/24
- positive half-years 2/4
- D1 UP PF 0.7575; failed time/regime transfer

Model finding:

- OHLC sequences carried measurable information about future MFE/MAE
- direct fixed-policy payoff ordering remained very weak
- LightGBM hazard and candidate performance exceeded the GRU
- a general sequence model did not solve the change in payoff meaning across time and D1 state

Formal interpretation:

`SEQUENCE_INFORMATION_EXISTS_BUT_GENERAL_SEQUENCE_MODELS_DID_NOT_CREATE_STABLE_PAYOFF_ORDERING_ACROSS_TIME_AND_D1_REGIMES`

Formal supported candidates remain **0**.

## Current next stage

`BTC_AI_V1_OHLC_EVENT_ANCHORED_TRAJECTORY_AND_SURVIVAL_FORENSIC_PREREGISTRATION`

Do not begin another broad model grid. First create an outcome-blind causal anchor registry covering range breaks, causal swings, expansion after compression, phase-transition starts, failed breaks and slope changes. Analyze continuation/reversal survival hazard by bars-since-anchor, ATR-distance, maximum extension, pullback depth, acceptance/rejection and H1/H4/D1 context. Freeze all anchor families, density gates and transfer tests before candidate PnL.

## Hard boundaries

- XM BTCUSD# OHLC only; no external or volume data
- MT5 broker-server time; no JST conversion
- closed bars only; exact M1 execution and no fabricated bars
- fixed spread 22.50 USD
- every count includes exact calendar months and monthly distribution
- no local-winner or sequence near-candidate rescue
- no PF, positive-month, minimum-count or D1-transfer gate reduction
- no use of 2026 for selection or support
- no portfolio, Shadow, Discord, MT5 orders, live-ready or final signal
- every stage must leave dated contracts, results, current state, next action and next-chat handoff
