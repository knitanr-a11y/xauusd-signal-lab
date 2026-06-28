# GML1 ML Synergy Exploration V4–V7 Result

Date: 2026-06-28  
Mode: audit-only

## Question

Can machine-learning behavior be adjusted so that the V1 structural candidates produce a stable positive-rate of at least 60% and Strong PF of at least 2.0?

## V4 — Direction-normalized hybrid meta-ML

Added direction-normalized features, V2 rule-risk inputs, classification plus Strong/Extreme expected-return regressors, global/direction/candidate specialists, empirical-percentile score normalization and model disagreement penalties.

Selected 2024:

- 159 trades
- Strong positive rate 61.01%
- Strong PF 1.900
- Extreme PF 1.553

Confirmation 2025:

- 354 trades
- Strong positive rate 41.24%
- Strong PF 0.894
- Extreme PF 0.790

No promotion.

## V5 — Resolved-only state and monthly refit

Added strictly causal virtual-history state. Every historical outcome entered state only after `exit_time <= current decision_time`. Tested expanding, rolling-365-day and decayed monthly refits.

Selected 2024:

- 145 trades
- Strong positive rate 58.62%
- Strong PF 1.666
- Extreme PF 1.344

Confirmation 2025:

- 237 trades
- Strong positive rate 46.84%
- Strong PF 1.118
- Extreme PF 0.968

No promotion. ExtraTrees monthly specialist configuration was not evaluated because its pre-registered 300-tree computation exceeded the bounded audit run; parameters were not changed after the fact.

## V6 — Static and stateful model consensus

Combined V4 and V5 scores, penalized model disagreement and V2 rule-risk count.

Selected 2024:

- 120 trades
- Strong positive rate 65.83%
- Strong PF 2.265
- Extreme PF 1.833

Confirmation 2025:

- 193 trades
- Strong positive rate 40.93%
- Strong PF 0.875
- Extreme PF 0.759

The requested target was achieved in selection but did not generalize.

## V7 — Resolved-only ML health-gate synergy

Applied health gates using only resolved shadow outcomes from V6-qualified candidates. The selected 2024 health rule was Strong-R EWMA with alpha 0.10 above zero.

Selected 2024:

- 109 trades
- Strong positive rate 67.89%
- Strong PF 2.503
- Extreme PF 2.029

Confirmation 2025:

- 76 trades
- Strong positive rate 40.79%
- Strong PF 0.883
- Extreme PF 0.752

A stricter Bayesian gate reduced 2025 damage to +3.39 Strong R but left only 30 trades, 46.67% positive rate and PF 1.214. It acted as a brake, not as a source of edge.

## Conclusion

Machine learning was actively used in V4–V7. It is not enabled in the live runtime because every selected configuration failed the unchanged 2025 confirmation.

The experiments show:

1. the current features can identify a very strong 2024 subset;
2. static, stateful and ensemble scores make correlated errors after the market regime changes;
3. resolved-only health logic can reduce exposure but cannot create missing alpha;
4. greater model complexity is not the current bottleneck;
5. a new independent entry structure or materially new causal data is required before another model search.

Controls remain OFF: live-ready, final signal, Discord and MT5 orders.
