# START HERE — BTC AI Candidate Research V1

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-ai-v1-data-acquisition`
- status: `BTC_AI_V1_OHLC_ONLY_ORDERING_AND_ADAPTATION_SEARCH_EXHAUSTED_THROUGH_STAGE35_NO_SUPPORTED_CANDIDATE`
- updated: `2026-08-04`

## Authority

Use only accepted XM `BTCUSD#` closed-bar OHLC:

- M1/M5/M15/H1/H4/D1
- MT5 broker-server naive time
- closed M15 decisions and exact M1 execution
- fixed spread 22.50 USD per completed 1 BTC trade
- no external-market, funding, open-interest, order-flow, tick-volume or real-volume features

Old BTC BCR, stacking and frozen candidates are not authority. Do not modify GOLD V19, Challenger C1, P75 or MOCHIPOYO.

## Unique latest handoff

`docs/btc_ai_v1/NEXT_CHAT_HANDOFF_BTC_AI_V1_OHLC_ADAPTATION_EXHAUSTED_STAGE36_20260804.md`

## Research status through Stage 35

- Stage 31 hard rolling 3/6/12M: no supported schedule;
- Stage 32 past-only drift/rank attribution: no supported live gate;
- Stage 33 full-history exponential recency 3/6/12/24M: no supported half-life;
- Stage 34 expanding/decay P90 consensus: no supported half-life;
- Stage 35 live-causal 1/4/12h cooldown: no supported configuration.

Formal supported candidates remain **0**. Candidate PnL and 2026 were not opened in Stages 31–35.

## Current stop rule

Further searches over windows, half-lives, thresholds, cooldowns, direction rescues, favorable months or D1 states are prohibited because they would mine the same consumed 2024–2025 OHLC information universe.

A future research cycle requires explicit user authorization for either:

1. a genuinely new causal information source; or
2. a new label/execution objective frozen before viewing its outcomes.

## Hard boundaries

- resolved-only history: `maturity_ns <= current refit_time`;
- previous complete month only for calibration;
- no 2026 selection;
- no candidate PnL;
- no post-result LONG/SHORT, month, D1 or volatility rescue;
- no external or volume data without explicit user authorization;
- Shadow, Discord, MT5 orders, live-ready and final signal remain OFF.
