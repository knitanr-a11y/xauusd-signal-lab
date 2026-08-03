# NEXT CHAT HANDOFF — BTC AI V1 OHLC state-transition cycles complete, local edges found, no supported candidate

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-ai-v1-data-acquisition`
- date: `2026-08-03`
- status: `BTC_AI_V1_OHLC_STATE_TRANSITION_LOCAL_EDGES_FOUND_NO_SUPPORTED_CANDIDATE`

## Authority

Use only the accepted XM `BTCUSD#` closed-bar OHLC snapshot.

- time: MT5 broker-server naive time
- decision: closed M15
- execution: exact next M1 open and exact M1 path
- fixed spread: 22.50 USD per completed 1 BTC trade
- same-M1 collision: SL first
- one-position non-overlap
- no external-market, funding, open-interest, order-flow, tick-volume or real-volume features

The unsolicited external-data branch content was rejected by the user. Active workflows, contracts, reports, handoff and downloader scripts were removed from the current tree. Git history retains the incident only for audit.

## Required read order

1. `START_HERE_BTC_AI_V1.md`
2. this handoff
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
16. `config/btc_ai_v1/current_state_20260803.json`
17. `config/btc_ai_v1/next_action_20260803.json`
18. `docs/btc_ai_v1/RESEARCH_HISTORY_INDEX.md`

Do not read deleted external-data paths or old handoffs before completing this order.

## Completed research

All three cycles used the four expanding validation folds covering exactly 24 calendar months, 2024-01 through 2025-12. The consumed 2026-01 through 2026-07 period was not opened in any of these cycles because no candidate reached the frozen development and transfer gates.

### Cycle A — one global model with OHLC state-transition features

- 100 causal OHLC features
- six outcome-blind phases and six transition types
- LightGBM depth-3 and regularized logistic models
- 48 candidates; 384 exact-M1 exit configurations
- positive-net configurations: 72
- PF >= 1.15 configurations: 0
- formal survivors: 0

Best near-setting:

- `ST6_010`, global LightGBM, base OHLC plus state, SHORT P97.5 first-cross
- 290 completed trades / 24 months = 12.08/month
- PF 1.1302, net +9,209.23
- positive months 12/24; positive half-years 3/4
- rejected without gate relaxation

### Cycle B — one expert per OHLC phase

Training, calibration and event emission were separated inside each phase.

- 48 raw candidates; 42 capability survivors
- 336 exact-M1 exit configurations
- positive-net configurations: 143
- PF >= 1.20 configurations: 32
- formal survivors: 0

Strong local patterns:

1. `EARLY_IMPULSE LONG`
   - 64 trades / 24 months = 2.67/month
   - PF 1.4538, net +3,797.81
   - positive months 13/24; positive half-years 4/4
   - failed frozen minimum of 96 trades

2. `RANGE_NEUTRAL LONG`
   - 268 / 24 = 11.17/month
   - PF 1.3704, net +15,805.22
   - positive months 17/24; positive half-years 4/4
   - failed frozen transition-concentration gate; no rescue

### Cycle C — one expert per OHLC transition

Training, calibration and event emission were separated inside each transition type. Transfer gates were defined across D1 UP / NEUTRAL / DOWN.

- 48 raw candidates; 26 capability survivors
- 208 exact-M1 exit configurations
- positive-net configurations: 89
- PF >= 1.20 configurations: 30
- formal survivors: 0

Strong local patterns:

1. `INTO_EARLY_IMPULSE LONG`
   - 78 trades / 24 months = 3.25/month
   - PF 1.6162, net +5,200.22
   - positive months 14/24; positive half-years 3/4
   - failed 96-trade minimum and D1-regime PF floor

2. `EXHAUSTION_TO_REVERSAL SHORT`
   - 79 / 24 = 3.29/month
   - PF 1.4931, net +6,755.63
   - positive months 12/24; positive half-years 2/4
   - density and time-persistence gates failed

## Formal interpretation

The root-cause hypothesis received partial support:

- a single global score did not separate state meaning strongly enough;
- phase-conditional and transition-conditional calibration produced materially higher local PF;
- early impulse and exhaustion/reversal are different OHLC objects and should not share one score scale;
- however the strongest local edges were sparse or dependent on insufficiently stable time/regime support;
- lowering the trade minimum, removing bad regimes, combining the two winners or opening 2026 would be post-result rescue and is prohibited.

Formal supported candidates remain **0**.

## Current next stage

`BTC_AI_V1_OHLC_SEQUENCE_TRANSITION_HAZARD_MULTITASK_PREREGISTRATION`

The next distinct method may use only OHLC and must model the sequence leading into a phase transition rather than score one static row. It should include all preregistered phases/transitions, not only the two locally profitable ones.

Required design direction:

- causal M15 sequence input with closed H1/H4/D1 context;
- small TCN or GRU plus a simple non-neural baseline;
- multi-task outputs for phase-transition hazard, direction-specific MFE/MAE and fixed-policy payoff;
- phase/transition-balanced training weights defined without outcome inspection;
- chronological expanding folds over 2024–2025;
- leave-one-D1-regime-out and leave-one-transition-type-out tests before PnL shortlist;
- retain the 96-trade and monthly-persistence requirements; do not reduce them because local patterns were sparse;
- 2026 remains diagnostic-only and opens only after a fully frozen robustness survivor.

## Hard boundaries

- no external data or volume fields;
- no use of 2026 for selection or support;
- no combination or rescue of `EARLY_IMPULSE LONG` and `EXHAUSTION_TO_REVERSAL SHORT`;
- no threshold, phase, transition, direction, month, exit or minimum-count relaxation;
- no portfolio, Shadow, Discord, MT5 order, live-ready or final signal;
- do not modify GOLD V19, Challenger C1, P75 or MOCHIPOYO.
