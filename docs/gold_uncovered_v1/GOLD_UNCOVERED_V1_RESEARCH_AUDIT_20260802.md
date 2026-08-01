# GOLD UNCOVERED V1 — Independent Multi-Vector Research Audit

Date: 2026-08-02  
Formal status: **`RETROSPECTIVE_MULTI_VECTOR_RESEARCH_COMPLETE_NO_FORMAL_CANDIDATE`**

## Executive conclusion

Four materially separate vectors were preregistered and evaluated from raw candle data without using V19, Challenger C1, E40 scores, ranks, wave states, episodes, runtime state, or their signal/trade ledgers as candidate inputs. No vector produced a complete formal candidate. No side deletion, threshold rescue, period deletion, volatility filter, hour filter, or post-result rule change was applied.

Existing V19 and Challenger C1 runtimes were not read or modified. This research ran entirely in the assistant execution environment using the retained authoritative raw candle files.

## Source authority

- Historical and sharp M1/H1/H4/D1 SHA256 values matched the frozen DATA_V3 source manifest.
- Old/sharp overlapping raw rows matched exactly.
- M15 was rebuilt from the validated full M1 union and matched all 81,781 historical broker M15 rows exactly.
- MT5 broker-server naive bar-open time was preserved.
- Higher-timeframe features became available only at bar-open plus timeframe.
- Exact M1 execution used TP20, SL10, 480 contiguous minutes, fixed spread 0.30 and SL-first same-minute collision.

## Study A — H4/D1 regime transitions

The originally proposed simple intraday families were withdrawn before outcome calculation because they duplicated previously audited price-action vectors. They were replaced by five H4/D1 regime-transition hypotheses.

- `D1_H4_ALIGNMENT_BREAK`: discovery n=55, PF=0.692, net=-74.61, complete gate=false.
- `D1_VOL_EXPANSION_CONTINUATION`: discovery n=3, PF=0.626, net=-4.36, complete gate=false.
- `H4_RANGE_TO_TREND_PULLBACK`: discovery n=13, PF=1.797, net=+19.29, complete gate=false.
- `D1_EXHAUSTION_REVERSAL`: discovery n=0, complete gate=false.
- `D1_H4_DISAGREEMENT_RESOLUTION`: discovery n=33, PF=0.732, net=-36.92, complete gate=false.

No family passed. Evaluation periods were not opened for this study.

## Study B — Tick-volume × price effort/result

- `VOLUME_ABSORPTION_REVERSAL`: discovery n=156, PF=1.196, net=+124.37, complete gate=false.
- `VOLUME_CLIMAX_CONTINUATION`: discovery n=217, PF=0.824, net=-181.10, complete gate=false.
- `DRYUP_PULLBACK_RESUMPTION`: discovery n=16, PF=0.362, net=-39.34, complete gate=false.
- `EFFORT_RESULT_DIVERGENCE_REVERSAL`: discovery n=127, PF=1.233, net=+112.47, complete gate=true.
- `VOLUME_STATE_RELEASE`: discovery n=0, complete gate=false.

The fixed discovery winner was `EFFORT_RESULT_DIVERGENCE_REVERSAL`. Untouched evaluation produced n=118, PF=1.553, net=+318.34 and DD=50.00.

- LONG: n=59, PF=2.733, net=+372.75.
- SHORT: n=59, PF=0.849, net=-54.41.
- Additional cost 0.60: PF=1.404.
- Four of five evaluation periods were positive.
- Month-block bootstrap P(net > 0)=0.9965.

The frozen both-direction contract failed because SHORT PF was below 1.0. LONG-only rescue is prohibited.

## Study C — Previous-day and multi-day reference levels

- `PREVDAY_BREAK_HOLD`: discovery n=185, PF=0.826, net=-128.77, complete gate=false.
- `PREVDAY_SWEEP_RECLAIM`: discovery n=213, PF=0.919, net=-62.51, complete gate=false.
- `PREVDAY_MIDPOINT_REJECTION`: discovery n=176, PF=1.160, net=+94.07, complete gate=false.
- `INSIDE_DAY_BREAKOUT`: discovery n=44, PF=1.006, net=+1.00, complete gate=false.
- `THREE_DAY_BALANCE_BREAK`: discovery n=59, PF=1.082, net=+18.49, complete gate=false.

No family passed. Evaluation periods were not opened for this study.

## Study D — Raw-candle native ML

Two fixed LightGBM classifiers were trained for LONG and SHORT using only causal M15/H1/H4/D1 raw-candle features. Training ended at 2024-06-30. Direction thresholds were label-free P95 values from 2024H2 prediction distributions.

- Calibration LONG AUC: 0.631.
- Calibration SHORT AUC: 0.571.
- Calibration portfolio: n=369, PF=4.562, net=+3144.60.

Evaluation from 2025H1 through 2026JUL:

- n=908.
- PF=0.944.
- net=-332.81.
- DD=618.84.
- LONG PF=0.833.
- SHORT PF=1.036.
- Additional cost 0.60 PF=0.862.
- Month-block bootstrap P(net > 0)=0.1485.

The initial ML accounting output included unresolved future-gap rows in the one-position ordering, producing NaN net/DD. The implementation was corrected to exclude unresolved rows exactly as required by the frozen exact-M1 contract; features, model parameters, thresholds and candidate rules were unchanged. The corrected evaluation failed decisively.

## Formal decision

`RETROSPECTIVE_MULTI_VECTOR_RESEARCH_COMPLETE_NO_FORMAL_CANDIDATE`

- Do not start a Shadow or Discord notifier from GU1.
- Do not delete SHORT from the volume study.
- Do not retune the ML thresholds or select only 2025 periods.
- Do not add time, volatility or side filters after these results.
- Do not repeat the withdrawn simple M15 families under new names.
- Any next study must be a newly preregistered structural vector and must acknowledge that the common historical data has now been repeatedly examined.

## Authorization

Research only. Shadow, Discord, AI judgement, MT5 order, live trading, promotion and merge remain unauthorized.
