# START HERE — GOLD SCALP M1 MIXTURE V1

Date: 2026-08-02  
Branch: `feature/gold-scalp-m1-mixture-v1-research`

## Formal status

`RETROSPECTIVE_M1_MIXTURE_RESEARCH_COMPLETE_NO_FORMAL_CANDIDATE`

## User-authorized boundaries

- stop loss must be 5 USD or less;
- profit target must be 5 USD or more;
- breakeven movement is allowed;
- research may choose a fixed or causal flexible exit at entry;
- exact M1 execution, fixed spread 0.30 and recorded spread gate 30 points;
- same-M1 protective stop first;
- one-position non-overlap.

## Completed studies

1. Thirteen high-frequency M1/M5 event engines, nine exit policies, TRAIN-only event-specific exit mapping, and separate LONG/SHORT LightGBM quality models.
2. A different raw 30-M1-sequence small CNN with nine exit outputs per direction.
3. Absolute-score and causal previous-60-day rank threshold ladders.

Both studies produced zero calibration passes and zero formal evaluation passes. Frequency was not the problem: the tested rows produced far more than 20 trades per month. Entry quality and forward stability failed.

## Important finding

All 22 event-side exit mappings had negative TRAIN mean PnL after an additional 0.60 cost. Breakeven was selected for only one mapping and ATR-dynamic exits for zero mappings. Flexible exit management did not rescue the tested entry families.

## Authoritative read order

1. `docs/gold_scalp_m1_mixture_v1/GOLD_SCALP_M1_MIXTURE_V1_RESEARCH_AUDIT_20260802.md`
2. `config/gold_scalp_m1_mixture_v1/formal_status_20260802.json`
3. `config/gold_scalp_m1_mixture_v1/next_action_20260802.json`
4. `docs/gold_scalp_m1_mixture_v1/REPRODUCTION_NOTE_20260802.md`

## Prohibitions

- do not retune breakeven triggers after results;
- do not select a favorable month, hour, side or exit after evaluation;
- do not lower TP below 5 or increase SL above 5;
- do not start Shadow, Discord, MT5 order or live trading;
- do not modify frozen V19 or Challenger C1.

Research only. No deployment or merge authorization follows from this branch.
