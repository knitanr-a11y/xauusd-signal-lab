# BTC AI V1 Stage 21 — Pairwise Ranking and Recency Adaptation Preregistration

Date: 2026-08-03  
Status: `FROZEN_BEFORE_PAIRWISE_RANKING_OUTCOMES`

This cycle directly optimizes score ordering. Continuous direct-payoff targets are converted to within-month ordinal quintiles for training only. Monthly grouping prevents the model from winning merely by learning that one calendar month had a higher unconditional payoff level.

AI methods:

- XGBoost `rank:pairwise`;
- CatBoost `YetiRank`;
- expanding training;
- recent rolling up-to-12-month training.

Targets, feature sets, directions and event rules yield at most 288 raw candidates. Development remains exactly 24 months, 2024-01 through 2025-12. The consumed 2026 seven-month period remains diagnostic only.
