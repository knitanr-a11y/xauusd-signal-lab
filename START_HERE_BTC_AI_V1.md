# START HERE — BTC AI Candidate Research V1

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-ai-v1-data-acquisition`
- status: `BTC_AI_V1_OHLC_2026_FAILURE_ROOT_CAUSE_IDENTIFIED_STATE_TRANSITION_RESEARCH_NEXT`
- updated: `2026-08-03`

## Scope and source authority

BTC専用のデータ・コスト・評価契約でゼロベース研究する。旧BTC BCR、旧stacking、旧5候補はauthorityにしない。GOLD V19、Challenger C1、P75、MOCHIPOYOを変更しない。

ユーザーの訂正により、外部市場データは使用しない。Binance等の取得・検証は非承認・非正本であり、Git履歴上の事故監査以外には使わない。

唯一の正本データは、受領・監査済みのXM `BTCUSD#` closed-bar snapshot:

- M1
- M5
- M15
- H1
- H4
- D1

時刻はMT5 broker-server time。固定spreadは1 BTC取引あたり22.50 USD。

## Unique latest handoff

`docs/btc_ai_v1/NEXT_CHAT_HANDOFF_BTC_AI_V1_OHLC_ROOT_CAUSE_DONE_STATE_TRANSITION_NEXT_20260803.md`

## Required read order

1. `START_HERE_BTC_AI_V1.md`
2. latest handoff above
3. `docs/btc_ai_v1/USER_SCOPE_CORRECTION_EXTERNAL_DATA_REJECTED_OHLC_AUTHORITY_20260803.md`
4. `docs/btc_ai_v1/BTC_AI_V1_OHLC_2026_FAILURE_ROOT_CAUSE_FORENSIC_20260803.md`
5. `config/btc_ai_v1/ohlc_2026_failure_root_cause_20260803.json`
6. `config/btc_ai_v1/current_state_20260803.json`
7. `config/btc_ai_v1/next_action_20260803.json`
8. `config/btc_ai_v1/source_data_manifest_20260803.json`
9. `config/btc_ai_v1/fixed_cost_contract_20260803.json`
10. `config/btc_ai_v1/frequency_reporting_contract_20260803.json`
11. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md`

Do not search old handoffs or other branches before completing this order.

## Current formal finding

The 2024–2025 winners failed in 2026 because the conditional meaning of their high-score OHLC state changed.

- SHORT opportunity did not disappear: 2026 SHORT-positive base rate remained 36.53%.
- D1-up share fell from 44.60% to 15.10%; D1-down share rose from 25.71% to 46.69%.
- D1 EMA20 slope / ATR mean reversed from +0.1243 to -0.1232.
- selected finalist events became much more extended: ret32/ATR changed from -0.150 to -1.154, distance below EMA50 from -0.280 to -0.876, range expansion from 2.31 to 2.91.
- model scores remained similar in distribution, but AUC fell to approximately 0.508–0.523.
- stop-first resolution increased and the thin PF 1.17–1.21 development edge reversed.
- fixed spread worsened the result but was not the primary cause; four of five candidates still lost at zero spread.
- a simple D1-up filter is not a valid explanation or authorized rescue because performance also deteriorated inside the same coarse D1 states.

Formal root cause:

`OHLC_STATE_TRANSITION_AND_CONDITIONAL_MEANING_SHIFT_CAUSED_LATE_SHORT_SELECTION`

Supported candidates remain **0**.

## Current next stage

`BTC_AI_V1_OHLC_STATE_TRANSITION_REPRESENTATION_AND_LEAVE_ONE_REGIME_OUT_DESIGN`

Continue immediately with OHLC only. Represent early impulse, mature extension, pullback, continuation, exhaustion and reversal, then freeze leave-one-regime-out and leave-one-transition-type-out validation before opening candidate results.

## Hard boundaries

- XM BTCUSD# only; no external market or non-candle data.
- MT5 broker-server time; no JST conversion.
- closed bars only; exact M1 execution and no fabricated bars.
- fixed spread 22.50 USD.
- every event/trade count includes exact calendar months and monthly distribution.
- no D1-only rescue or post-result threshold, direction, month, feature, target, exit or horizon rescue.
- 2026 remains diagnostic and cannot be reused as untouched support.
- no portfolio, Shadow, Discord, MT5 orders, live-ready or final signal.
- every stage must leave dated results, current state, next action and next-chat handoff.
