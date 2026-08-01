# GOLD SCALP AI V1 — Consolidated Research Audit

Date: 2026-08-02  
Formal status: **`RETROSPECTIVE_SCALP_AI_RESEARCH_COMPLETE_NO_FORMAL_CANDIDATE`**

## Executive conclusion

The requested fixed-dollar GOLD scalping objective was tested on the validated DATA_V3 raw candle union:

- TP5 / SL3 / 120 exact M1 minutes;
- TP7.5 / SL4 / 180 exact M1 minutes;
- TP10 / SL5 / 240 exact M1 minutes;
- desired positive-PnL win rate at least 60%;
- exact M1 execution, fixed spread 0.30, recorded spread gate 30 points, same-M1 collision SL first;
- one-position non-overlap;
- M5 closed-bar decisions with causal M15/H1/H4/D1 context.

No corrected calibration row passed. No formal evaluation candidate was opened. No Shadow, Discord, AI judgement, MT5 order, live trading or deployment is authorized.

This result does **not** prove that a 60% GOLD scalper is impossible. It shows that the tested broad every-M5 raw-candle classifier, including the V19-inspired score normalization and update schedule, did not produce it.

## Data and causality audit

- M1 union rows: **1,266,508**
- Complete M5 rows rebuilt from M1: **252,581**
- Complete M15 rows rebuilt from M1: **83,554**
- Complete causal feature rows: **251,967**
- Source range: **2023-01-03 01:00:00 to 2026-07-31 23:13:00**
- MT5 broker-server naive time preserved.
- Higher-timeframe bars became available only after their close.
- Unresolved future-gap outcomes were excluded.
- Independent Python re-evaluation sampled 600 exact-M1 trades: **0 PnL/reason/exit mismatches**.
- One-position non-overlap audit: **PASS**.
- Frozen V19 and Challenger C1 were not read as candidate inputs and were not modified.

## Tested AI structures

### V1 — fixed absolute probability

Two separate LightGBM variants were trained:

1. `LOCAL_ONLY`: causal M5 and M15 features.
2. `LOCAL_PLUS_HTF`: local features plus H1, H4 and D1 context.

LONG and SHORT were modeled separately for each of the three TP/SL contracts. The fixed threshold ladder was P90, P95, P97.5 and P99.

**Corrected result:** no threshold passed the 2024H2 calibration gate.

The closest absolute-score row by pooled PF was:

- variant: `LOCAL_ONLY`
- contract: `TP7P5_SL4_H180`
- threshold: P99
- n: 197
- win rate: 36.04%
- PF: 0.989
- net: -5.37
- additional-cost PF: 0.881

The highest corrected absolute-score win rate was only **36.04%**, not 60%.

### V1B — V19-style 60-day directional rank

Absolute model probabilities were replaced with a causal direction-specific percentile rank:

- previous 60 calendar days;
- current MT5 server date excluded;
- minimum 100 reference rows;
- fixed rank ladder P90, P95, P97.5 and P99.

**Corrected result:** no threshold passed.

The closest rank row by pooled PF was:

- variant: `LOCAL_ONLY`
- contract: `TP7P5_SL4_H180`
- rank: P99
- n: 204
- win rate: 34.80%
- PF: 0.950
- net: -26.41
- additional-cost PF: 0.847

The highest corrected rolling-rank win rate was **34.90%**.

### V1C — V19-style semiannual expanding update

A separate diagnostic retrained the `LOCAL_PLUS_HTF` model at January/July boundaries using only outcomes resolved before each boundary. The selected rank threshold still had to be chosen on 2024H2 and remain fixed afterward.

No contract passed the 2024H2 calibration gate, so no trade-level evaluation candidate was opened.

Directional AUC diagnostics also weakened after calibration. Representative examples:

- TP5/SL3: 2024H2 AUC LONG 0.567 / SHORT 0.602; 2026H1 LONG 0.500 / SHORT 0.503.
- TP7.5/SL4: 2024H2 0.568 / 0.586; 2026H1 0.493 / 0.512.
- TP10/SL5: 2024H2 0.547 / 0.577; 2026H1 0.492 / 0.508.

This indicates that score normalization alone was not the main problem. The tested candle features had insufficient stable discrimination for the short TP-first labels.

## Corrected calibration range

Across all corrected rows:

- win rate range: approximately **22.12% to 36.04%**;
- pooled PF: below 1.0 for every row;
- net: negative for every row;
- additional-cost PF: below 1.0 for every row;
- no 60% win-rate row;
- no both-direction formal candidate.

The theoretical break-even win rates without timeout effects are about:

- TP5/SL3: 37.5%;
- TP7.5/SL4: 34.8%;
- TP10/SL5: 33.3%.

With an additional 0.30 cost per trade they rise to approximately 41.3%, 37.4% and 35.3%. The corrected candidates did not show adequate margin even against those lower break-even levels.

## Period-partition incident

An audit found that an early implementation labeled all rows before 2025 as `CAL`, mixing the 2023–2024H1 training period into the intended 2024H2 calibration period. That produced misleading interim 60% calibration figures.

Actions taken:

1. the issue was recorded in `period_partition_incident.json`;
2. all pre-fix threshold decisions and selected candidate files were invalidated;
3. the partition was corrected to:
   - TRAIN: before 2024-07-01;
   - CAL: 2024-07-01 through 2024-12-31;
   - evaluation blocks: 2025H1, 2025H2, 2026H1 and 2026JUL;
4. V1 and V1B were rerun from scratch;
5. every corrected threshold failed.

The earlier 60% figures must not be used.

## Research interpretation

The current failure is specific:

- entering from a broad every-M5 opportunity grid;
- using raw candle, volume, trend, volatility and higher-timeframe features;
- using separate LONG/SHORT LightGBM classifiers;
- using fixed small-dollar TP-first labels;
- applying either absolute probability, rolling rank, or semiannual expanding updates.

The result does not rule out a sparse structural scalper. It argues against trying to rescue this model with post-result hour, month, volatility or side deletion filters.

## Recommended next research boundary

A new study should be **event-first**, not every-M5-first:

1. preregister a sparse causal market event such as a sweep/reclaim, impulse-pullback, effort/result divergence, or a frozen V19 episode boundary;
2. generate only the first eligible entry per event;
3. use AI only as a directional/quality filter inside those predeclared events;
4. keep TP5/SL3, TP7.5/SL4 and TP10/SL5 unchanged for comparison;
5. require new prospective data before any deployment claim.

Because the 2023–2026 history has now been repeatedly examined, any newly discovered retrospective lead must remain research-only until a fresh prospective Shadow sample exists.

## Authorization

Research complete. No Shadow, Discord notifier, AI discretionary judgement, MT5 order, live trading, promotion or merge authorization.
