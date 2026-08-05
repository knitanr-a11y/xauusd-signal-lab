# BTC AI V1 Stage 05 — Independent Second Search Cycle Preregistration

Date: 2026-08-03  
Status: `FROZEN_BEFORE_SECOND_CYCLE_OUTCOME_COMPUTATION`

The first cycle ended `PROMISING_NOT_ROBUST_NO_FINALIST`. This second cycle does not tune or rescue its breakout-SHORT thresholds. It uses expanding-fold supervised directional rank models defined before computing second-cycle validation outcomes.

## Fixed design

- exact M15 closed-bar decisions and exact M1 replay;
- fixed spread 22.50 USD per BTC;
- direction-specific label: 1.5 ATR target before 1.0 ATR stop within 720 exact M1 minutes;
- SL first on same-M1 collisions;
- invalid if exact M1 entry or continuity is unavailable;
- four expanding folds, each with a six-calendar-month past-only calibration period;
- 2026-01 through 2026-07 remains untouched and locked.

## Candidate registry

The registry is fixed at 144 definitions:

- four predeclared models;
- three causal feature sets;
- LONG and SHORT separately;
- calibration percentiles P90, P95 and P97.5;
- first-cross and four-M15-bar cooldown event policies.

No absolute probability threshold is tuned.

## Required frequency reporting

Every reported event or completed-trade count must include its calendar-month denominator, active months, trades per month, zero-trade months and monthly min/median/max. A total count alone is incomplete.

## Gates and prohibitions

Capability, development, robustness and final-test gates remain those already frozen. First-cycle candidates are not seeds. No model, feature set, percentile, side, label, exit or horizon may be modified after results. The untouched final test may be opened only for a frozen robustness finalist.