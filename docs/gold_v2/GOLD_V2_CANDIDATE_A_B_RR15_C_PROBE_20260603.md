# GOLD V2 Candidate A + B(RR>=1.5) + C probe

Created: 2026-06-03
Status: audit-only / not runtime approved

## User instruction

Candidate A remains unchanged. Candidate B should be restricted to RR >= 1.5. Because B becomes too sparse, search for an additional Candidate C from still-unused clusters.

## Definitions

Candidate A:

```text
10-day lookback
top5 all-consensus stack-only gate
profit = candidateA_profit_r
```

Candidate B RR>=1.5:

```text
Candidate A rejected
AND regime == MID_MIXED
AND trend_eff96 >= 0.633155
AND top_variant RR >= 1.5
profit = stacked_capped3_profit_r
```

Candidate C search universe:

```text
not Candidate A
not Candidate B RR>=1.5
profit = stacked_capped3_profit_r
```

## A and B(RR>=1.5) baseline

| Policy | Count | Win rate | PF | TotalR | AvgR | Worst | MaxDD |
|---|---:|---:|---:|---:|---:|---:|---:|
| A only | 89 | 71.91% | 4.32 | +179.5R | +2.017R | -5R | 7R |
| B RR>=1.5 only | 10 | 70.00% | 5.25 | +17.0R | +1.700R | -3R | 3R |
| A + B RR>=1.5 | 99 | 71.72% | 4.39 | +196.5R | +1.985R | -5R | 7R |

Monthly A + B(RR>=1.5):

| Month | Count | Win rate | PF | TotalR | Worst |
|---|---:|---:|---:|---:|---:|
| 2026-03 | 54 | 74.07% | 5.27 | +94.0R | -3R |
| 2026-04 | 24 | 66.67% | 3.67 | +48.0R | -5R |
| 2026-05 | 20 | 70.00% | 3.64 | +47.5R | -5R |
| 2026-06 | 1 | 100.00% | inf | +7.0R | +7R |

## Best Candidate C found

Candidate C recommendation:

```text
range96 >= 100.43
AND range96 <= 117.86
```

C-only, after excluding A and B(RR>=1.5):

| Count | Win rate | PF | TotalR | AvgR | Worst | MaxDD |
|---:|---:|---:|---:|---:|---:|---:|
| 26 | 84.62% | 5.83 | +29.0R | +1.115R | -3R | 3R |

Interpretation:

```text
C is an intermediate range-width / volatility-shape addon.
It is not the same as Candidate A's consensus stack gate.
It is also not the same as B's MID_MIXED trend-efficiency RR>=1.5 gate.
```

## A + B(RR>=1.5) + C result

| Policy | Count | Win rate | PF | TotalR | AvgR | Worst | MaxDD | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A only | 89 | 71.91% | 4.32 | +179.5R | +2.017R | -5R | 7R | 2 |
| A+B RR>=1.5 | 99 | 71.72% | 4.39 | +196.5R | +1.985R | -5R | 7R | 2 |
| A+B RR>=1.5+C | 125 | 74.40% | 4.52 | +225.5R | +1.804R | -5R | 7R | 2 |

Monthly A+B(RR>=1.5)+C:

| Month | Count | Win rate | PF | TotalR | Worst | MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| 2026-03 | 58 | 75.86% | 5.52 | +99.5R | -3R | 3R |
| 2026-04 | 34 | 70.59% | 3.83 | +56.5R | -5R | 7R |
| 2026-05 | 31 | 74.19% | 3.75 | +60.5R | -5R | 5R |
| 2026-06 | 2 | 100.00% | inf | +9.0R | +2R | 0R |

## Why this is better than A+B full

Previously, unrestricted B added 32 trades and produced:

```text
A+B full: 121 trades / 71.90% WR / PF 4.17 / +209.5R
```

The new composition gives:

```text
A+B(RR>=1.5)+C: 125 trades / 74.40% WR / PF 4.52 / +225.5R
```

It restores the missing trade count while improving win rate and PF.

## Current interpretation

This is now the best practical composition in this audit set:

```text
A = main high-conviction stack signal
B = RR>=1.5 MID_MIXED trend-efficiency supplement
C = intermediate range96 volatility-shape supplement
```

The April/May issue improves:

```text
April A only: 21 trades -> A+Brr+C: 34 trades
May A only: 14 trades -> A+Brr+C: 31 trades
```

While keeping win rate above 70% in March/April/May.

## Caveat

Candidate C was discovered from the rejected set after seeing audit results. It must be validated with strict no-lookahead before runtime adoption.

Next required step:

```text
A + B(RR>=1.5) + C strict walk-forward validation on all folds/months.
```
