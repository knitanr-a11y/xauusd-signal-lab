# BTC AI V1 H4 Outside-Bar Post-hoc Mechanism Audit Result

- formal status: `BTC_AI_V1_H4_OUTSIDE_POST_HOC_MECHANISM_AUDIT_NO_ROBUST_MECHANISM`
- branch: `feature/btc-h4-outside-mechanism-audit`
- preregistration commit: `e06fd33f2e1faf4c39c74c1c3c6a5e74f27e76a0`
- evidence: `POST_HOC_MECHANISM_AUDIT_ON_CONSUMED_HISTORY_NOT_SELECTION_VALIDATION`
- direct promotion: prohibited
- Stage55: unchanged
- MT5 orders / live trading / live-ready / final signal / Discord: OFF

## Formal period 2024–2026-07

| mechanism | trades | win rate | PF | net USD | max DD | stress gate |
|---|---:|---:|---:|---:|---:|---|
| `H4_OUTSIDE_EXTREME_CONTINUATION_CLOSE_BREAK` | 165 | 30.91% | 0.795 | -7479.35 | 11496.03 | FAIL |
| `H4_OUTSIDE_FAILED_EXTREME_REJECTION` | 176 | 32.95% | 0.903 | -3800.88 | 11448.77 | FAIL |
| `H4_OUTSIDE_IMMEDIATE_EXTREME_REVERSION` | 262 | 31.68% | 0.834 | -9346.44 | 18449.53 | FAIL |
| `H4_OUTSIDE_MIDPOINT_REVERSION_BODY_CONFIRM` | 84 | 36.90% | 1.107 | 1766.22 | 2316.09 | FAIL |

## Main finding

- The original midpoint-reversion mechanism remained the only combined-period positive form: PF 1.107 and +1,766.22 USD.
- It still failed the preregistered stress gate: 2026 PF 0.717, largest-winner-removed PF 1.025, double-cost PF 0.993, net/DD 0.763, and LONG PF 0.788.
- Immediate reversion, continuation breakout, and failed-extreme rejection were all negative over the combined period.
- The mechanism changed sign across time: immediate reversion and failed rejection were strong in 2026 but poor in 2024–2025, while midpoint reversion was good in 2024–2025 and poor in 2026.
- This supports a regime-dependent interpretation, but no live-time causal regime gate was preregistered; therefore no slice or variant is promoted.

## Temporal slices

### `H4_OUTSIDE_EXTREME_CONTINUATION_CLOSE_BREAK`

| period | trades | win rate | PF | net USD |
|---|---:|---:|---:|---:|
| 2023_SANITY | 42 | 42.86% | 0.997 | -6.74 |
| 2024 | 59 | 35.59% | 0.891 | -1278.66 |
| 2025 | 82 | 28.05% | 0.791 | -4247.91 |
| 2026_01_07 | 24 | 29.17% | 0.563 | -1952.78 |
| COMBINED_2024_2026_07 | 165 | 30.91% | 0.795 | -7479.35 |
| RECENT_2026_07 | 3 | 66.67% | 12.074 | 580.30 |

### `H4_OUTSIDE_FAILED_EXTREME_REJECTION`

| period | trades | win rate | PF | net USD |
|---|---:|---:|---:|---:|
| 2023_SANITY | 54 | 38.89% | 0.896 | -367.27 |
| 2024 | 63 | 31.75% | 0.952 | -622.95 |
| 2025 | 81 | 29.63% | 0.687 | -6628.46 |
| 2026_01_07 | 32 | 43.75% | 1.704 | 3450.53 |
| COMBINED_2024_2026_07 | 176 | 32.95% | 0.903 | -3800.88 |
| RECENT_2026_07 | 1 | 0.00% | 0.000 | -356.02 |

### `H4_OUTSIDE_IMMEDIATE_EXTREME_REVERSION`

| period | trades | win rate | PF | net USD |
|---|---:|---:|---:|---:|
| 2023_SANITY | 77 | 31.17% | 0.585 | -2248.39 |
| 2024 | 87 | 22.99% | 0.496 | -10089.73 |
| 2025 | 121 | 31.40% | 0.736 | -7712.20 |
| 2026_01_07 | 54 | 46.30% | 2.170 | 8455.49 |
| COMBINED_2024_2026_07 | 262 | 31.68% | 0.834 | -9346.44 |
| RECENT_2026_07 | 8 | 62.50% | 2.524 | 1200.72 |

### `H4_OUTSIDE_MIDPOINT_REVERSION_BODY_CONFIRM`

| period | trades | win rate | PF | net USD |
|---|---:|---:|---:|---:|
| 2023_SANITY | 24 | 45.83% | 0.948 | -68.16 |
| 2024 | 26 | 42.31% | 1.130 | 652.82 |
| 2025 | 39 | 38.46% | 1.322 | 2324.84 |
| 2026_01_07 | 19 | 26.32% | 0.717 | -1211.44 |
| COMBINED_2024_2026_07 | 84 | 36.90% | 1.107 | 1766.22 |
| RECENT_2026_07 | 3 | 33.33% | 0.973 | -10.56 |

## Pipeline

| mechanism | raw | dedup | exact M1 | one-position | resolved-only | suppressed |
|---|---:|---:|---:|---:|---:|---:|
| `H4_OUTSIDE_IMMEDIATE_EXTREME_REVERSION` | 339 | 339 | 339 | 339 | 339 | 0 |
| `H4_OUTSIDE_MIDPOINT_REVERSION_BODY_CONFIRM` | 108 | 108 | 108 | 108 | 108 | 0 |
| `H4_OUTSIDE_EXTREME_CONTINUATION_CLOSE_BREAK` | 207 | 207 | 207 | 207 | 207 | 0 |
| `H4_OUTSIDE_FAILED_EXTREME_REJECTION` | 231 | 231 | 231 | 230 | 230 | 1 |

## Stress diagnostics

| mechanism | PF | net/DD | 2024 PF | 2025 PF | 2026 PF | max-winner-removed PF | double-cost PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| `H4_OUTSIDE_IMMEDIATE_EXTREME_REVERSION` | 0.834 | -0.507 | 0.496 | 0.736 | 2.170 | 0.807 | 0.748 |
| `H4_OUTSIDE_MIDPOINT_REVERSION_BODY_CONFIRM` | 1.107 | 0.763 | 1.130 | 1.322 | 0.717 | 1.025 | 0.993 |
| `H4_OUTSIDE_EXTREME_CONTINUATION_CLOSE_BREAK` | 0.795 | -0.651 | 0.891 | 0.791 | 0.563 | 0.750 | 0.714 |
| `H4_OUTSIDE_FAILED_EXTREME_REJECTION` | 0.903 | -0.332 | 0.952 | 0.687 | 1.704 | 0.864 | 0.814 |

## Direction diagnostics

| mechanism | direction | trades | PF | net USD |
|---|---|---:|---:|---:|
| `H4_OUTSIDE_EXTREME_CONTINUATION_CLOSE_BREAK` | LONG | 85 | 0.673 | -6203.36 |
| `H4_OUTSIDE_EXTREME_CONTINUATION_CLOSE_BREAK` | SHORT | 80 | 0.927 | -1275.99 |
| `H4_OUTSIDE_FAILED_EXTREME_REJECTION` | LONG | 89 | 0.807 | -3979.82 |
| `H4_OUTSIDE_FAILED_EXTREME_REJECTION` | SHORT | 87 | 1.010 | 178.95 |
| `H4_OUTSIDE_IMMEDIATE_EXTREME_REVERSION` | LONG | 129 | 0.808 | -5401.23 |
| `H4_OUTSIDE_IMMEDIATE_EXTREME_REVERSION` | SHORT | 133 | 0.861 | -3945.21 |
| `H4_OUTSIDE_MIDPOINT_REVERSION_BODY_CONFIRM` | LONG | 42 | 0.788 | -1813.52 |
| `H4_OUTSIDE_MIDPOINT_REVERSION_BODY_CONFIRM` | SHORT | 42 | 1.448 | 3579.74 |

## Causal volatility diagnostics

| mechanism | regime | trades | PF | net USD |
|---|---|---:|---:|---:|
| `H4_OUTSIDE_EXTREME_CONTINUATION_CLOSE_BREAK` | HIGH | 124 | 0.802 | -5883.50 |
| `H4_OUTSIDE_EXTREME_CONTINUATION_CLOSE_BREAK` | LOW | 41 | 0.765 | -1595.85 |
| `H4_OUTSIDE_FAILED_EXTREME_REJECTION` | HIGH | 130 | 0.957 | -1348.38 |
| `H4_OUTSIDE_FAILED_EXTREME_REJECTION` | LOW | 46 | 0.695 | -2452.49 |
| `H4_OUTSIDE_IMMEDIATE_EXTREME_REVERSION` | HIGH | 179 | 0.842 | -6888.55 |
| `H4_OUTSIDE_IMMEDIATE_EXTREME_REVERSION` | LOW | 83 | 0.808 | -2457.90 |
| `H4_OUTSIDE_MIDPOINT_REVERSION_BODY_CONFIRM` | HIGH | 59 | 1.332 | 3939.16 |
| `H4_OUTSIDE_MIDPOINT_REVERSION_BODY_CONFIRM` | LOW | 25 | 0.533 | -2172.93 |

Direction and volatility slices are diagnostic only. They were not used to select or rescue a mechanism.

## Global one-position audit

| period | trades | win rate | PF | net USD | max DD |
|---|---:|---:|---:|---:|---:|
| 2023_SANITY | 157 | 37.58% | 0.784 | -2202.29 | 3253.18 |
| 2024 | 170 | 32.35% | 0.790 | -7493.86 | 9148.18 |
| 2025 | 237 | 33.76% | 0.842 | -8550.34 | 12604.83 |
| 2026_01_07 | 104 | 37.50% | 1.389 | 6449.76 | 3326.18 |
| COMBINED_2024_2026_07 | 511 | 34.05% | 0.910 | -9594.44 | 18625.25 |
| RECENT_2026_07 | 13 | 61.54% | 2.833 | 1946.16 | 360.63 |

## Boundary

- No mechanism can rescue the rejected H4 outside base.
- No maximum-PF variant is selected.
- No fresh Shadow is authorized from this post-hoc audit.
- Any future continuation must be a new prospective development design with a new cutoff and no backfill.
- No future result, open bar, future ATR, or future H4 state was used in entry construction.
- Exact M1 entry and SL-first same-M1 collision rules were maintained.
- Stage55 was not modified.
