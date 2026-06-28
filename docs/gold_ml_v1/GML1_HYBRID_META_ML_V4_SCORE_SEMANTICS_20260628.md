# GML1 Hybrid Meta-ML V4 Score Semantics

Date: 2026-06-28
Mode: audit-only

This addendum is frozen before V4 model results are calculated.

## Architectures

- `GLOBAL_ONLY`: use the pooled global classifier and regressors.
- `SHRUNK_SPECIALIST`: combine global, matching direction specialist, and matching candidate specialist using the weights frozen in the V4 contract. Missing specialists fall back to global weight.

## Stable component scale

For each fitted model version, predictions for its own resolved training registry are stored. Every future prediction is converted to an empirical percentile against that training prediction distribution. This prevents a raw probability or regression scale shift from silently changing the gate between annual model versions.

Percentiles are calculated independently for:

- probability of positive Strong R;
- predicted Strong R;
- predicted Extreme R.

No future-year prediction distribution is used to normalize scores.

## Behaviors

- `P_ONLY`: probability percentile.
- `S_ONLY`: predicted Strong-R percentile.
- `E_ONLY`: predicted Extreme-R percentile.
- `PS_MIN`: minimum of probability and Strong-R percentiles.
- `PSE_MIN`: minimum of probability, Strong-R and Extreme-R percentiles.
- `PSE_MEAN_LCB`: mean of all three percentiles minus the frozen disagreement penalty multiplied by their standard deviation and the specialist-level prediction disagreement.

## Gates

Each behavior is evaluated with the retention fractions frozen in the V4 contract. The selected 2024 retention fraction is converted to a numeric score threshold from the 2023 training-score distribution. The numeric threshold is then unchanged for 2025 and 2026 model versions because all behavior scores are training-distribution percentiles.

A proposal must also satisfy any explicit probability threshold selected from the frozen grid. `P_ONLY`, `S_ONLY` and `E_ONLY` may use probability threshold 0.0 as no additional probability gate; consensus behaviors use the frozen probability threshold grid.

## Rule-risk features

The twelve V2 composite rule flags and their total count are input features only. They never remove a proposal directly in V4.
