# BTC AI V1 — H4 day-open bad-loss exclusion audit

Date: 2026-08-05  
branch: `feature/btc-day-open-loss-exclusion-audit`  
preregistration commit: `bf1c2f72998f435a61864924360427a3536c2399`

## Formal conclusion

`BTC_AI_V1_DAY_OPEN_LOSS_EXCLUSION_NO_FILTER_PASSED_ALL_ANTI_OVERFIT_GATES`

The frozen parent `LOCK_0P25ATR_AFTER_2ATR` was not modified. Five fixed causal risk flags and one fixed composite were evaluated once. No configuration passed all preregistered retention, temporal, economic, robustness, direction, concentration, and loss-selectivity gates.

## Formal period 2024–2026 July

| Configuration | Trades | Retained | Win rate | PF | Net USD | Max DD | Net/DD | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Any two risk flags skip | 804 | 59.2% | 60.07% | 1.318 | +72,046.44 | 14,351.97 | 5.020 | REJECT |
| H4 range-shock skip | 1,105 | 81.4% | 56.11% | 1.274 | +76,118.22 | 14,012.01 | 5.432 | REJECT |
| Third+ flip same-day skip | 1,025 | 75.5% | 58.54% | 1.267 | +77,753.54 | 16,135.72 | 4.819 | REJECT |
| Near day-open skip | 399 | 29.4% | 64.66% | 1.245 | +33,908.21 | 18,234.89 | 1.860 | REJECT |
| Control +0.25ATR lock | 1,357 | 100.0% | 56.67% | 1.225 | +85,951.14 | 18,996.77 | 4.525 | CONTROL |
| Counter-body skip | 1,357 | 100.0% | 56.67% | 1.225 | +85,951.14 | 18,996.77 | 4.525 | REJECT |
| Weak close skip | 1,069 | 78.8% | 56.88% | 1.207 | +63,937.85 | 17,026.53 | 3.755 | REJECT |

## Most informative non-passing variants

### H4 range-shock skip

- Skip when the closed H4 true range exceeds 2.0× the median true range of the prior 20 closed H4 bars.
- 1,105 trades; 81.4% retained.
- Win rate 56.11%, PF 1.274, net +76,118.22 USD, Max DD 14,012.01 USD, Net/DD 5.432.
- 2024/2025/2026 were all positive.
- It failed the frozen gate because win rate fell by 0.56 points, net was below 80,000 USD, and loss-selectivity did not reproduce in 2025.

### Any two of five risk flags skip

- Risk flags: counter-body, weak directional close, near day-open, H4 range shock, third-or-later same-day state episode.
- 804 trades; only 59.2% retained.
- Win rate 60.07%, PF 1.318, net +72,046.44 USD, Max DD 14,351.97 USD, Net/DD 5.020.
- 2024/2025/2026 and LONG/SHORT were all positive.
- It failed because it removed 40.8% of trades, net fell below the parent, and formal loss-capture advantage was 4.49 points versus the frozen 5-point requirement.

## Loss selectivity

| Filter | Formal loss capture | Formal profit sacrificed | Edge | 2025 edge | 2026 edge |
|---|---:|---:|---:|---:|---:|
| Counter-body skip | 0.00% | 0.00% | +0.00pt | +0.00pt | +0.00pt |
| Weak close skip | 19.15% | 20.34% | -1.19pt | +2.92pt | -12.33pt |
| Near day-open skip | 63.82% | 63.22% | +0.60pt | -2.34pt | +6.84pt |
| H4 range-shock skip | 27.22% | 24.32% | +2.90pt | -3.10pt | +6.54pt |
| Third+ flip same-day skip | 23.70% | 21.10% | +2.60pt | -1.49pt | +0.94pt |
| Any two risk flags skip | 40.64% | 36.15% | +4.49pt | +0.36pt | +1.93pt |

No fixed flag consistently removed more loss dollars than profit dollars in both 2025 and 2026 by a sufficient margin. This is the main reason not to promote the attractive aggregate results.

## Important implementation finding

`SKIP_COUNTER_BODY` skipped zero state episodes. At a new day-open desired-state episode, the flip structure in this dataset made the counter-body predicate redundant. It is retained as a negative result and was not replaced after outcomes.

## Causality and parity audit

- Raw closed-H4 events: 7,647
- Completed trades across seven configs: 9,807
- Unresolved: 0
- Parent control parity: 1,885 versus 1,885 trades, exact match
- Independent Python/Numba parity all pass
- Synthetic tests all pass
- A skipped state episode remains flat until the next state flip; no delayed same-state re-entry.
- Future/open/as-of features: 0.
- Exact M1 entry; no fallback.
- Stage55 and the frozen parent candidate were not modified.

## Boundary

- No filter replaces the parent candidate.
- No Fresh Shadow was created.
- No direction/month/year/volatility rescue.
- MT5 orders, live trading, live-ready, final signal, Discord, and automatic promotion remain OFF.

## Next independent question

Because static entry flags did not pass, the next anti-overfit test may examine causal loss-cluster controls based only on already resolved prior trades. This must be a separately frozen cycle and must not tune the thresholds from the results above.
