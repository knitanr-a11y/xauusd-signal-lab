# START HERE — BTC AI Candidate Research V1

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative archive/runtime branch: `feature/btc-ai-v1-data-acquisition`
- current status: `BTC_AI_V1_STAGE55_ACTIVE_FULL95_ALL_Q20_SHADOW_IMPLEMENTED_NOT_ACTIVATED`
- updated: `2026-08-06`

## Read first

1. `docs/btc_ai_v1/NEXT_CHAT_HANDOFF_BTC_AI_V1_FULL95_ALL_Q20_SHADOW_READY_20260806.md`
2. `config/btc_ai_v1/current_state_full95_all_q20_shadow_20260806.json`
3. `config/btc_ai_v1/next_action_full95_all_q20_shadow_20260806.json`
4. `config/btc_ai_v1/full95_all_q20_prospective_shadow_contract_20260806.json`
5. `docs/btc_ai_v1/BTC_AI_V1_FULL95_ALL_Q20_PROSPECTIVE_SHADOW_V1_20260806.md`
6. `runtime/btc_ai_v1/full95_all_q20_shadow_v1/docs/RUNBOOK_JA.md`
7. `runtime/btc_ai_v1/full95_all_q20_shadow_v1/docs/RESEARCH_INTEGRITY_RULES_JA.md`
8. `config/btc_ai_v1/current_state_stage55_20260804.json`
9. `config/btc_ai_v1/stage55_dual_reverse_short_shadow_contract_20260804.json`
10. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX_V2_20260804.md`

Read all ten from beginning to end before changing either Shadow.

## Fixed market-data authority

Use only accepted XM `BTCUSD#` closed-bar OHLC:

- M1/M5/M15/H1/H4/D1;
- MT5 broker-server naive time;
- closed-bar decisions and exact-M1 execution;
- missing exact entry M1 means invalid or fail-closed according to the frozen runtime contract; no nearest-M1 fallback;
- same-M1 protective/target collision resolves protective first;
- fixed round-trip cost 22.50 USD per completed 1 BTC trade;
- no external-market, funding, open-interest, order-flow, tick-volume or real-volume features.

Old BTC BCR, stacking and frozen candidates are not authority for this BTC AI V1 line. Do not modify GOLD V19, Challenger C1, P75 or MOCHIPOYO.

## Stage55 frozen prospective Shadow

Stage55 remains active on the user PC.

- activation status: `READY_NO_BACKFILL_ACTIVATED`;
- activation cutoff: `2026-08-04 10:52:00` MT5;
- accepted candidates at activation: 0;
- runtime state: `%LOCALAPPDATA%/xauusd_signal_lab/btc_stage55_shadow`;
- minimum conclusion gate per family: 20 closed trades and 6 calendar months.

Do not change its model, Q70, confirmation, stop, target, hold, family membership, cutoff, state or no-backfill behavior.

## Full95 All-Q20 matched-pair Shadow

The GitHub package is implemented at:

`runtime/btc_ai_v1/full95_all_q20_shadow_v1`

Current state:

- GitHub implementation: complete;
- user-PC activation: not performed;
- activation cutoff: not yet created;
- compared arms: `CONTROL_LOCK_0P25ATR` and `AI_FULL95_ALL_Q20`;
- model/95 features/Q20 threshold: frozen;
- historical AI results: consumed post-hoc evidence only;
- only post-activation observations count;
- no automatic retraining, candidate switching or promotion;
- MT5 orders, live trading, live-ready and final signal: OFF.

This package is separate from Stage55 and must not read or reset the Stage55 runtime state.

## Research-integrity boundary

The 2023–2026-07 history has been heavily consumed. Historical model comparisons, including Full95 versus LONG-only or Top30, are not formal holdout evidence. Do not use later historical comparisons to replace the frozen Full95 candidate during this Shadow.

The first primary prospective review requires at least:

- 6 calendar months;
- 100 closed Control trades;
- 20 AI skips;
- skips in at least 2 quarters;
- positive AI-minus-Control net;
- AI PF not below Control;
- AI maximum drawdown not above Control;
- at least 75% trade retention;
- negative skipped-Control counterfactual net.

No automatic promotion follows even if the gate is met.

## Historical record

The prior Stage00–55 and simple-rule research history remains preserved in:

- `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX_V2_20260804.md`;
- `docs/btc_ai_v1/BTC_AI_V1_CUMULATIVE_RESEARCH_RECORD_THROUGH_STAGE55_AND_SIMPLE_RULE_NEXT_20260804.md`;
- the separate `feature/btc-simple-discretionary-rule-research` branch for the simple deterministic-rule cycle.
