# BTC AI V1 Stage 12 — Diverse AI Exploratory Cycle Preregistration

Date: 2026-08-03  
Status: `FROZEN_BEFORE_DIVERSE_AI_OUTCOME_COMPUTATION`

The 2026-01 through 2026-07 period was consumed by the second-cycle untouched test. This third cycle cannot create retrospective support from that period. It is an exploratory rolling-development comparison whose survivors, if any, require new future prospective data.

## Objective

Test whether materially different nonlinear AI model classes can produce stable causal directional ranking signals on the same accepted BTCUSD# data and fixed 22.50 USD spread contract.

## Fixed source and execution

- M15 closed-bar decision grid;
- exact M1 entry and exit replay;
- fixed spread 22.50 USD per completed 1 BTC trade;
- same-M1 TP/SL collision: SL first;
- no interpolation or timeframe fallback;
- development window: 2024-01 through 2025-12, exactly 24 calendar months;
- 2026 data: forensic diagnostics only, prohibited for candidate selection.

## Fixed supervised label

Direction-specific 1.5 ATR target before 1.0 ATR stop within 720 exact M1 minutes, using the same causal label and maturity rules as the second cycle. Keeping the label fixed isolates model-class effects.

## Fixed AI model classes

1. `XGB_D3` — XGBoost histogram tree ensemble, shallow depth 3.
2. `CAT_D4` — CatBoost gradient boosting, depth 4.
3. `EXTRA_D8` — ExtraTrees randomized tree ensemble, depth 8.
4. `HGB_L15` — sklearn histogram gradient boosting, 15 leaves.
5. `RANK_ENSEMBLE` — arithmetic mean of percentile ranks from the four preregistered base models, computed fold by fold without outcome-based weights.

## Fixed feature sets

- `MTF_CONTEXT`
- `FULL_CAUSAL`

Both directions are modeled separately.

## Fixed candidate conversion

- past-six-month calibration per expanding fold;
- percentiles P90, P95 and P97.5;
- event policies: first cross from below and four-M15-bar cooldown;
- 5 model definitions × 2 feature sets × 2 directions × 3 percentiles × 2 event policies = 120 raw candidates.

## Capability, development and robustness

- outcome-blind density and exact-M1 capability gates remain unchanged;
- maximum capability survivors: 60;
- execution grid and development gates remain unchanged;
- robustness controls remain unchanged;
- maximum development shortlist: 20;
- maximum exploratory prospective-ready definitions: 5 after overlap control;
- no 2026 final-test replay is permitted.

## Reporting

Every count must include evaluation calendar months, total trades, trades per calendar month, active months, zero months and monthly min/median/max.

## No-rescue boundaries

- no model deletion after outcomes;
- no hyperparameter, percentile, side, label, exit or horizon change after outcomes;
- no 2026 selection or support claim;
- no portfolio, Shadow, Discord, MT5 order, live-ready or final signal;
- any survivor is `EXPLORATORY_PROSPECTIVE_ONLY` until new future data exists.
