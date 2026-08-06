# BTC AI V1 Long-Horizon Odd Geometry Research Result

- formal status: `BTC_AI_V1_LONG_HORIZON_ODD_GEOMETRY_ALL_FOUR_REJECTED`
- branch: `feature/btc-long-horizon-odd-rule-research`
- preregistration commit: `04caaec9c37a24b8fa9b95249fdd2923676af435`
- evidence: `RETROSPECTIVE_EXPLORATORY_EVIDENCE_ON_CONSUMED_HISTORY`
- Stage55: unchanged
- MT5 orders / live trading / live-ready / final signal / Discord: OFF

## Formal period 2024–2026-07

| family | trades | win rate | PF | net USD | max DD | decision |
|---|---:|---:|---:|---:|---:|---|
| `D1_NR7_NEXT_DAY_FIRST_M15_CLOSE_BREAK` | 75 | 25.33% | 0.651 | -3835.28 | 4245.36 | `REJECTED_RETROSPECTIVE_EXPLORATORY_EVIDENCE` |
| `D1_TWO_COLOR_ALTERNATION_OPENING_RANGE_CONTINUATION` | 102 | 30.39% | 0.679 | -6841.83 | 8463.20 | `REJECTED_RETROSPECTIVE_EXPLORATORY_EVIDENCE` |
| `H4_INSIDE_BAR_NEXT_16_M15_FIRST_CLOSE_BREAK` | 855 | 33.22% | 0.857 | -20409.32 | 24020.08 | `REJECTED_RETROSPECTIVE_EXPLORATORY_EVIDENCE` |
| `H4_OUTSIDE_EXTREME_CLOSE_MIDPOINT_REVERSION` | 84 | 36.90% | 1.107 | 1766.22 | 2316.09 | `REJECTED_RETROSPECTIVE_EXPLORATORY_EVIDENCE` |

## Pipeline

| family | raw | dedup | exact M1 | one-position | resolved-only | missing exact M1 | suppressed |
|---|---:|---:|---:|---:|---:|---:|---:|
| `D1_NR7_NEXT_DAY_FIRST_M15_CLOSE_BREAK` | 102 | 102 | 102 | 102 | 102 | 0 | 0 |
| `H4_INSIDE_BAR_NEXT_16_M15_FIRST_CLOSE_BREAK` | 1196 | 1196 | 1195 | 1193 | 1193 | 1 | 2 |
| `H4_OUTSIDE_EXTREME_CLOSE_MIDPOINT_REVERSION` | 108 | 108 | 108 | 108 | 108 | 0 | 0 |
| `D1_TWO_COLOR_ALTERNATION_OPENING_RANGE_CONTINUATION` | 139 | 139 | 139 | 139 | 139 | 0 | 0 |

## Temporal slices

### `D1_NR7_NEXT_DAY_FIRST_M15_CLOSE_BREAK`

| period | trades | win rate | PF | net USD |
|---|---:|---:|---:|---:|
| 2023_SANITY | 27 | 22.22% | 0.567 | -712.23 |
| 2024 | 29 | 27.59% | 0.686 | -1325.01 |
| 2025 | 28 | 32.14% | 0.933 | -266.13 |
| 2026_01_07 | 18 | 11.11% | 0.204 | -2244.14 |
| COMBINED_2024_2026_07 | 75 | 25.33% | 0.651 | -3835.28 |
| RECENT_2026_07 | 4 | 0.00% | 0.000 | -566.85 |

### `D1_TWO_COLOR_ALTERNATION_OPENING_RANGE_CONTINUATION`

| period | trades | win rate | PF | net USD |
|---|---:|---:|---:|---:|
| 2023_SANITY | 37 | 32.43% | 0.837 | -468.87 |
| 2024 | 42 | 35.71% | 0.926 | -537.45 |
| 2025 | 39 | 35.90% | 0.714 | -2681.75 |
| 2026_01_07 | 21 | 9.52% | 0.227 | -3622.63 |
| COMBINED_2024_2026_07 | 102 | 30.39% | 0.679 | -6841.83 |
| RECENT_2026_07 | 4 | 0.00% | 0.000 | -692.02 |

### `H4_INSIDE_BAR_NEXT_16_M15_FIRST_CLOSE_BREAK`

| period | trades | win rate | PF | net USD |
|---|---:|---:|---:|---:|
| 2023_SANITY | 338 | 30.77% | 0.581 | -9136.06 |
| 2024 | 336 | 34.23% | 0.881 | -6081.13 |
| 2025 | 301 | 32.56% | 0.892 | -6300.95 |
| 2026_01_07 | 218 | 32.57% | 0.755 | -8027.24 |
| COMBINED_2024_2026_07 | 855 | 33.22% | 0.857 | -20409.32 |
| RECENT_2026_07 | 32 | 46.88% | 1.120 | 353.75 |

### `H4_OUTSIDE_EXTREME_CLOSE_MIDPOINT_REVERSION`

| period | trades | win rate | PF | net USD |
|---|---:|---:|---:|---:|
| 2023_SANITY | 24 | 50.00% | 1.084 | 96.68 |
| 2024 | 26 | 42.31% | 1.130 | 652.82 |
| 2025 | 39 | 38.46% | 1.322 | 2324.84 |
| 2026_01_07 | 19 | 26.32% | 0.717 | -1211.44 |
| COMBINED_2024_2026_07 | 84 | 36.90% | 1.107 | 1766.22 |
| RECENT_2026_07 | 3 | 33.33% | 0.973 | -10.56 |

## Gate diagnostics

| family | combined PF | net/DD | 2024 PF | 2025 PF | 2026 PF | max winner removed PF | double-cost PF | final |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `D1_NR7_NEXT_DAY_FIRST_M15_CLOSE_BREAK` | 0.651 | -0.903 | 0.686 | 0.933 | 0.204 | 0.580 | 0.549 | REJECT |
| `H4_INSIDE_BAR_NEXT_16_M15_FIRST_CLOSE_BREAK` | 0.857 | -0.850 | 0.881 | 0.892 | 0.755 | 0.843 | 0.744 | REJECT |
| `H4_OUTSIDE_EXTREME_CLOSE_MIDPOINT_REVERSION` | 1.107 | 0.763 | 1.130 | 1.322 | 0.717 | 1.025 | 0.993 | REJECT |
| `D1_TWO_COLOR_ALTERNATION_OPENING_RANGE_CONTINUATION` | 0.679 | -0.808 | 0.926 | 0.714 | 0.227 | 0.634 | 0.601 | REJECT |

## Direction diagnostics

| family | direction | trades | PF | net USD |
|---|---|---:|---:|---:|
| `D1_NR7_NEXT_DAY_FIRST_M15_CLOSE_BREAK` | LONG | 40 | 0.613 | -2300.53 |
| `D1_NR7_NEXT_DAY_FIRST_M15_CLOSE_BREAK` | SHORT | 35 | 0.695 | -1534.74 |
| `D1_TWO_COLOR_ALTERNATION_OPENING_RANGE_CONTINUATION` | LONG | 56 | 0.791 | -2351.23 |
| `D1_TWO_COLOR_ALTERNATION_OPENING_RANGE_CONTINUATION` | SHORT | 46 | 0.555 | -4490.60 |
| `H4_INSIDE_BAR_NEXT_16_M15_FIRST_CLOSE_BREAK` | LONG | 452 | 0.802 | -15396.77 |
| `H4_INSIDE_BAR_NEXT_16_M15_FIRST_CLOSE_BREAK` | SHORT | 403 | 0.922 | -5012.56 |
| `H4_OUTSIDE_EXTREME_CLOSE_MIDPOINT_REVERSION` | LONG | 42 | 0.788 | -1813.52 |
| `H4_OUTSIDE_EXTREME_CLOSE_MIDPOINT_REVERSION` | SHORT | 42 | 1.448 | 3579.74 |

## Causal volatility diagnostics

| family | regime | trades | PF | net USD |
|---|---|---:|---:|---:|
| `D1_NR7_NEXT_DAY_FIRST_M15_CLOSE_BREAK` | HIGH | 57 | 0.377 | -5997.25 |
| `D1_NR7_NEXT_DAY_FIRST_M15_CLOSE_BREAK` | LOW | 18 | 2.603 | 2161.97 |
| `D1_TWO_COLOR_ALTERNATION_OPENING_RANGE_CONTINUATION` | HIGH | 51 | 0.770 | -2716.86 |
| `D1_TWO_COLOR_ALTERNATION_OPENING_RANGE_CONTINUATION` | LOW | 51 | 0.566 | -4124.97 |
| `H4_INSIDE_BAR_NEXT_16_M15_FIRST_CLOSE_BREAK` | HIGH | 246 | 1.023 | 1050.06 |
| `H4_INSIDE_BAR_NEXT_16_M15_FIRST_CLOSE_BREAK` | LOW | 609 | 0.776 | -21459.39 |
| `H4_OUTSIDE_EXTREME_CLOSE_MIDPOINT_REVERSION` | HIGH | 59 | 1.332 | 3939.16 |
| `H4_OUTSIDE_EXTREME_CLOSE_MIDPOINT_REVERSION` | LOW | 25 | 0.533 | -2172.93 |

These direction/volatility slices are diagnostic only and were not used to rescue or redefine a family.

## Global one-position audit

| period | trades | win rate | PF | net USD | max DD |
|---|---:|---:|---:|---:|---:|
| 2023_SANITY | 419 | 31.26% | 0.626 | -10057.98 | 11863.76 |
| 2024 | 422 | 34.60% | 0.890 | -7315.38 | 11037.35 |
| 2025 | 398 | 32.91% | 0.890 | -8517.07 | 16530.84 |
| 2026_01_07 | 269 | 29.37% | 0.677 | -13950.02 | 14866.29 |
| COMBINED_2024_2026_07 | 1089 | 32.69% | 0.841 | -29782.46 | 32946.83 |
| RECENT_2026_07 | 42 | 38.10% | 0.839 | -707.09 | 1728.67 |

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
