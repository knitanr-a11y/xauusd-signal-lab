# NEXT CHAT HANDOFF — BTC AI V1 OHLC sequence multi-task complete, no support, event-anchor forensic next

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-ai-v1-data-acquisition`
- date: `2026-08-03`
- status: `BTC_AI_V1_OHLC_SEQUENCE_INFORMATION_FOUND_NO_STABLE_PAYOFF_ORDERING`

## Authority

Use only the accepted XM `BTCUSD#` closed-bar OHLC snapshot.

- MT5 broker-server time
- closed M15 decision
- exact next M1 open and exact M1 path
- fixed spread: 22.50 USD per completed 1 BTC trade
- no external-market, funding, open-interest, order-flow, tick-volume or real-volume features

## Required read order

1. `START_HERE_BTC_AI_V1.md`
2. this handoff
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
16. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md`

Do not read deleted external-data paths or old handoffs before completing this order.

## Sequence experiment completed

Development covered exactly 24 calendar months, 2024-01 through 2025-12. The consumed 2026-01 through 2026-07 period was not opened.

Inputs:

- 64 consecutive closed M15 bars, equal to 16 hours;
- latest fully closed H1/H4/D1 OHLC context;
- 100,948 continuous sequence/target rows.

Targets:

- first named transition within 16 future M15 bars;
- LONG/SHORT MFE and MAE over 480 exact M1 bars;
- LONG/SHORT fixed-policy payoff with 1 ATR stop, 2 ATR target and 480-minute maximum hold.

Models:

- LightGBM lag/summary sequence baseline;
- small shared GRU multi-task model.

Candidates and execution:

- 32 raw definitions;
- all 32 passed outcome-blind capability gates;
- candidate frequency: 250–1,156 events over 24 months, or 10.42–48.17 events/month;
- 256 exact-M1 execution configurations;
- 88 configurations had positive net;
- zero configurations reached PF 1.20;
- provisional development survivors: 0.

Therefore transfer, bootstrap, matched-random and 2026 diagnosis were not opened.

## Strongest configurations

### LightGBM SHORT payoff tail

`SQ9_009__S1.0_T2.0_H480`

- 580 completed trades / 24 months = 24.17/month
- monthly min / median / max: 4 / 23.5 / 60
- PF 1.1539
- net +21,262.16
- DD 8,877.90
- positive months 13/24
- positive half-years 3/4
- failed PF 1.20 and 15-positive-month gates

Half-years:

- 2024H1: 108 trades, PF 1.0392, +836.12
- 2024H2: 159, PF 1.2024, +7,830.97
- 2025H1: 146, PF 0.9315, -2,850.01
- 2025H2: 167, PF 1.4233, +15,445.08

The selected P95 tail improved the fixed-policy target relative to all rows in every fold, but the improvement was too thin for monthly persistence.

### GRU SHORT path-edge tail

`SQ9_030__S1.0_T2.0_H720`

- 363 / 24 months = 15.13/month
- monthly min / median / max: 4 / 15.5 / 30
- PF 1.1496
- net +13,276.96
- DD 8,037.61
- positive months 13/24
- positive half-years 2/4

Half-years:

- 2024H1: PF 0.7164
- 2024H2: PF 0.9823
- 2025H1: PF 1.4573
- 2025H2: PF 1.1249

D1 regimes:

- DOWN: 68 trades, PF 1.4606
- NEUTRAL: 134, PF 1.5100
- UP: 161, PF 0.7575

The GRU relation appeared mainly in 2025 and outside D1-up conditions. It failed time and regime invariance.

## Model-level findings

- LightGBM hazard balanced accuracy: 0.333–0.469.
- GRU hazard balanced accuracy: 0.196–0.281.
- LightGBM MFE/MAE Spearman: approximately 0.150–0.247.
- LightGBM fixed-payoff Spearman: approximately 0.000–0.055.
- GRU path-edge Spearman: approximately 0.023–0.102.
- GRU fixed-payoff Spearman: approximately -0.006–0.038.

Formal interpretation:

`SEQUENCE_INFORMATION_EXISTS_BUT_GENERAL_SEQUENCE_MODELS_DID_NOT_CREATE_STABLE_PAYOFF_ORDERING_ACROSS_TIME_AND_D1_REGIMES`

The issue is not absence of OHLC sequence information. Future excursion size is partially predictable. The failure is converting it into stable trade payoff without knowing the causal event anchor and its maturity.

## Current formal state

- supported candidates: 0
- no near-candidate rescue
- no 2026 opening
- no portfolio, Shadow, Discord, MT5 order, live-ready or final signal

## Current next stage

`BTC_AI_V1_OHLC_EVENT_ANCHORED_TRAJECTORY_AND_SURVIVAL_FORENSIC_PREREGISTRATION`

Do not launch another broad model grid first. Begin with a forensic and outcome-blind anchor registry covering all causal anchor families:

1. range-break start;
2. causal rolling swing high/low;
3. first large expansion candle after compression;
4. phase-transition start;
5. failed break / return-inside event;
6. EMA-slope sign or acceleration change.

For each anchor, describe the trajectory using bars-since-anchor, ATR-distance-since-anchor, maximum extension, pullback depth, acceptance/rejection and higher-timeframe phase. Then estimate continuation/reversal survival hazard by anchor age. Freeze the anchor families, density gates and transfer tests before candidate PnL.

Do not select only previously profitable early-impulse or exhaustion-reversal anchors.

## Reproducibility package

- `BTC_AI_V1_OHLC_SEQUENCE_MULTITASK_RESEARCH_20260803.zip`
- SHA256: `532b37a89c0b1365af04288a3cc47e83462d990dd7d40b5c825d9c8b8bbcf7ca`
- 57 files; expansion-tested
- raw candles and external data are not included

## Hard boundaries

- XM BTCUSD# OHLC only;
- no use of 2026 for selection or support;
- no PF, positive-month, minimum-count or D1-transfer gate relaxation;
- no rescue or combination of prior local patterns and sequence near-candidates;
- no portfolio, Shadow, Discord, MT5 order, live-ready or final signal;
- do not modify GOLD V19, Challenger C1, P75 or MOCHIPOYO.
