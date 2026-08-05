# NEXT CHAT HANDOFF — BTC AI V1 Stage 31 rolling adaptation complete, no supported schedule

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-ai-v1-data-acquisition`
- date: `2026-08-04`
- status: `BTC_AI_V1_OHLC_ROLLING_ADAPTIVE_RECALIBRATION_NO_SUPPORTED_SCHEDULE`

## Required read order

1. `START_HERE_BTC_AI_V1.md`
2. this handoff
3. `docs/btc_ai_v1/BTC_AI_V1_OHLC_ROLLING_ADAPTIVE_RECALIBRATION_RESULT_20260804.md`
4. `config/btc_ai_v1/ohlc_rolling_adaptive_recalibration_result_20260804.json`
5. `docs/btc_ai_v1/BTC_AI_V1_OHLC_ROLLING_ADAPTIVE_RECALIBRATION_REPRODUCIBILITY_MANIFEST_20260804.md`
6. `config/btc_ai_v1/current_state_20260804.json`
7. `config/btc_ai_v1/next_action_20260804.json`
8. `config/btc_ai_v1/ohlc_drift_attribution_rank_stability_forensic_contract_20260804.json`

## Stage 31 accepted result

- authoritative XM `BTCUSD#` source hashes matched;
- 125,567 state rows × 100 OHLC-only features;
- 24 months × 4 schedules × 2 directions = 192 evaluations;
- all 192 available;
- leakage violations 0;
- rolling schedules supported: 0;
- candidate PnL and 2026 unopened.

Mean AUC deltas versus EXPANDING:

- ROLLING_3M: LONG -0.00666; SHORT -0.02506;
- ROLLING_6M: LONG -0.00182; SHORT -0.01684;
- ROLLING_12M: LONG +0.00035; SHORT -0.01031.

No direction record passed all frozen gates, and no same schedule passed LONG and SHORT.

## Next frozen stage

`BTC_AI_V1_OHLC_DRIFT_ATTRIBUTION_AND_RANK_STABILITY_FORENSIC`

Use Stage31 2024-2025 prediction audits only to distinguish sample-loss, score-rank instability and label-meaning drift. Stage32 is diagnostic-only and cannot select a new signal or open PnL.

## Hard boundaries

- no 2026;
- no candidate PnL;
- no current validation-month or future labels in diagnostic inputs intended for a later live gate;
- no post-result month or D1 rescue;
- no external or volume data;
- Shadow, Discord, MT5 orders, live-ready and final signal remain OFF.
