# BTC AI V1 Weird Deterministic Rule Research Result

- formal status: `BTC_AI_V1_WEIRD_DETERMINISTIC_RULES_ALL_FOUR_REJECTED`
- branch: `feature/btc-weird-deterministic-rule-research`
- preregistration commit: `3f01e84a7fd660f35b0f9fd4d63048177e7974ed`
- evidence: `RETROSPECTIVE_EXPLORATORY_EVIDENCE_ON_CONSUMED_HISTORY`
- Stage55: unchanged
- MT5 orders / live trading / live-ready / final signal / Discord: OFF

## Formal period 2024–2026-07

| family | trades | win rate | PF | net USD | max DD | decision |
|---|---:|---:|---:|---:|---:|---|
| `BROKER_DAY_FIRST_FOUR_M15_RANGE_FIRST_CLOSE_BREAK` | 799 | 31.66% | 0.732 | -42213.06 | 42727.34 | `REJECTED_RETROSPECTIVE_EXPLORATORY_EVIDENCE` |
| `FIVE_M15_COLOR_STREAK_FIRST_OPPOSITE_FADE` | 745 | 34.63% | 0.938 | -9003.29 | 21029.18 | `REJECTED_RETROSPECTIVE_EXPLORATORY_EVIDENCE` |
| `FOUR_M15_ALTERNATING_COLOR_RANGE_BREAK` | 1548 | 32.82% | 0.813 | -52551.14 | 54673.13 | `REJECTED_RETROSPECTIVE_EXPLORATORY_EVIDENCE` |
| `ROUND_1000_OPEN_ANCHORED_SWEEP_CLOSE_BACK` | 8365 | 33.70% | 0.866 | -247245.06 | 249395.30 | `REJECTED_RETROSPECTIVE_EXPLORATORY_EVIDENCE` |

## Pipeline

| family | raw | dedup | exact M1 | one-position | resolved-only | missing exact M1 | suppressed |
|---|---:|---:|---:|---:|---:|---:|---:|
| `FIVE_M15_COLOR_STREAK_FIRST_OPPOSITE_FADE` | 979 | 979 | 978 | 966 | 966 | 1 | 12 |
| `FOUR_M15_ALTERNATING_COLOR_RANGE_BREAK` | 2388 | 2388 | 2385 | 2074 | 2074 | 3 | 311 |
| `ROUND_1000_OPEN_ANCHORED_SWEEP_CLOSE_BACK` | 20786 | 20786 | 20774 | 9595 | 9595 | 12 | 11179 |
| `BROKER_DAY_FIRST_FOUR_M15_RANGE_FIRST_CLOSE_BREAK` | 1090 | 1090 | 1089 | 1089 | 1089 | 1 | 0 |

## Temporal slices

### `BROKER_DAY_FIRST_FOUR_M15_RANGE_FIRST_CLOSE_BREAK`

| period | trades | win rate | PF | net USD |
|---|---:|---:|---:|---:|
| 2023_SANITY | 290 | 29.66% | 0.570 | -8915.39 |
| 2024 | 305 | 33.11% | 0.659 | -19420.72 |
| 2025 | 316 | 33.86% | 0.914 | -5753.59 |
| 2026_01_07 | 178 | 25.28% | 0.496 | -17038.75 |
| COMBINED_2024_2026_07 | 799 | 31.66% | 0.732 | -42213.06 |
| RECENT_2026_07 | 27 | 25.93% | 0.474 | -1685.11 |

### `FIVE_M15_COLOR_STREAK_FIRST_OPPOSITE_FADE`

| period | trades | win rate | PF | net USD |
|---|---:|---:|---:|---:|
| 2023_SANITY | 221 | 28.96% | 0.555 | -7867.37 |
| 2024 | 290 | 34.83% | 0.959 | -2271.54 |
| 2025 | 296 | 32.09% | 0.799 | -13515.60 |
| 2026_01_07 | 159 | 38.99% | 1.300 | 6783.85 |
| COMBINED_2024_2026_07 | 745 | 34.63% | 0.938 | -9003.29 |
| RECENT_2026_07 | 22 | 31.82% | 0.655 | -931.72 |

### `FOUR_M15_ALTERNATING_COLOR_RANGE_BREAK`

| period | trades | win rate | PF | net USD |
|---|---:|---:|---:|---:|
| 2023_SANITY | 526 | 30.23% | 0.584 | -13938.65 |
| 2024 | 646 | 29.41% | 0.733 | -30972.66 |
| 2025 | 599 | 35.89% | 0.924 | -8703.72 |
| 2026_01_07 | 303 | 33.99% | 0.741 | -12874.76 |
| COMBINED_2024_2026_07 | 1548 | 32.82% | 0.813 | -52551.14 |
| RECENT_2026_07 | 40 | 42.50% | 1.056 | 220.31 |

### `ROUND_1000_OPEN_ANCHORED_SWEEP_CLOSE_BACK`

| period | trades | win rate | PF | net USD |
|---|---:|---:|---:|---:|
| 2023_SANITY | 1230 | 32.52% | 0.651 | -37713.96 |
| 2024 | 3127 | 32.40% | 0.838 | -107024.55 |
| 2025 | 3543 | 34.60% | 0.893 | -92003.12 |
| 2026_01_07 | 1695 | 34.22% | 0.852 | -48217.39 |
| COMBINED_2024_2026_07 | 8365 | 33.70% | 0.866 | -247245.06 |
| RECENT_2026_07 | 195 | 33.33% | 0.814 | -4807.12 |

## Gate diagnostics

| family | combined PF | net/DD | 2024 PF | 2025 PF | 2026 PF | max winner removed PF | double-cost PF | final |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `FIVE_M15_COLOR_STREAK_FIRST_OPPOSITE_FADE` | 0.938 | -0.428 | 0.959 | 0.799 | 1.300 | 0.921 | 0.835 | REJECT |
| `FOUR_M15_ALTERNATING_COLOR_RANGE_BREAK` | 0.813 | -0.961 | 0.733 | 0.924 | 0.741 | 0.806 | 0.713 | REJECT |
| `ROUND_1000_OPEN_ANCHORED_SWEEP_CLOSE_BACK` | 0.866 | -0.991 | 0.838 | 0.893 | 0.852 | 0.865 | 0.780 | REJECT |
| `BROKER_DAY_FIRST_FOUR_M15_RANGE_FIRST_CLOSE_BREAK` | 0.732 | -0.988 | 0.659 | 0.914 | 0.496 | 0.722 | 0.646 | REJECT |

## Direction diagnostics

| family | direction | trades | PF | net USD |
|---|---|---:|---:|---:|
| `BROKER_DAY_FIRST_FOUR_M15_RANGE_FIRST_CLOSE_BREAK` | LONG | 409 | 0.694 | -25008.51 |
| `BROKER_DAY_FIRST_FOUR_M15_RANGE_FIRST_CLOSE_BREAK` | SHORT | 390 | 0.773 | -17204.55 |
| `FIVE_M15_COLOR_STREAK_FIRST_OPPOSITE_FADE` | LONG | 360 | 0.844 | -11813.02 |
| `FIVE_M15_COLOR_STREAK_FIRST_OPPOSITE_FADE` | SHORT | 385 | 1.041 | 2809.74 |
| `FOUR_M15_ALTERNATING_COLOR_RANGE_BREAK` | LONG | 777 | 0.791 | -29074.96 |
| `FOUR_M15_ALTERNATING_COLOR_RANGE_BREAK` | SHORT | 771 | 0.834 | -23476.18 |
| `ROUND_1000_OPEN_ANCHORED_SWEEP_CLOSE_BACK` | LONG | 4242 | 0.837 | -153455.15 |
| `ROUND_1000_OPEN_ANCHORED_SWEEP_CLOSE_BACK` | SHORT | 4123 | 0.897 | -93789.92 |

## Causal volatility diagnostics

| family | regime | trades | PF | net USD |
|---|---|---:|---:|---:|
| `BROKER_DAY_FIRST_FOUR_M15_RANGE_FIRST_CLOSE_BREAK` | HIGH | 396 | 0.766 | -20768.87 |
| `BROKER_DAY_FIRST_FOUR_M15_RANGE_FIRST_CLOSE_BREAK` | LOW | 403 | 0.690 | -21444.19 |
| `FIVE_M15_COLOR_STREAK_FIRST_OPPOSITE_FADE` | HIGH | 433 | 1.003 | 270.44 |
| `FIVE_M15_COLOR_STREAK_FIRST_OPPOSITE_FADE` | LOW | 312 | 0.814 | -9273.72 |
| `FOUR_M15_ALTERNATING_COLOR_RANGE_BREAK` | HIGH | 697 | 0.884 | -16981.88 |
| `FOUR_M15_ALTERNATING_COLOR_RANGE_BREAK` | LOW | 851 | 0.735 | -35569.26 |
| `ROUND_1000_OPEN_ANCHORED_SWEEP_CLOSE_BACK` | HIGH | 5389 | 0.910 | -117990.92 |
| `ROUND_1000_OPEN_ANCHORED_SWEEP_CLOSE_BACK` | LOW | 2976 | 0.762 | -129254.15 |

These direction/volatility slices are diagnostic only and were not used to rescue or redefine a family.

## Global one-position audit

| period | trades | win rate | PF | net USD | max DD |
|---|---:|---:|---:|---:|---:|
| 2023_SANITY | 1956 | 31.13% | 0.621 | -58509.68 | 58742.45 |
| 2024 | 3531 | 32.94% | 0.851 | -105882.32 | 113822.03 |
| 2025 | 3881 | 34.32% | 0.886 | -104385.19 | 111682.68 |
| 2026_01_07 | 1922 | 33.87% | 0.835 | -59066.97 | 61692.82 |
| COMBINED_2024_2026_07 | 9334 | 33.70% | 0.865 | -269334.48 | 272183.24 |
| RECENT_2026_07 | 237 | 34.18% | 0.831 | -5017.26 | 7107.54 |

## Causality and runtime audit

- Candidate creation used only closed OHLC and information available at the decision timestamp.
- CSV latest row was treated as closed by contract.
- Exact M1 entry was required; missing exact M1 invalidated the candidate with no fallback.
- Same-M1 TP/SL collision used SL-first.
- Post-entry missing M1 intervals did not create synthetic bars; the position remained open and hold counted existing M1 bars only.
- One-position was applied within each family; cross-family global one-position was audit-only.
- Health gate was OFF / not applicable.
- No unresolved trades were assigned a future result.
- Stage55 was not modified.
