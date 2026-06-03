# GOLD V2 Candidate A addon probe from unused/rejected clusters

Created: 2026-06-03
Status: audit-only / not runtime approved

## User intent

Candidate A is strong and remains the main candidate, but April and May adoption count declines. The goal is to keep Candidate A as the core and add another vector from unused/rejected clusters if it can raise count without destroying win rate/PF.

## Source used

Only Candidate A rejected clusters were searched.

```text
Candidate A kept: 89
Candidate A rejected: 262
Test months: 2026-03 to 2026-06
```

Candidate B uses capped3 profit for safety:

```text
B profit = stacked_capped3_profit_r
```

## Candidate A baseline

| Policy | Count | Win rate | PF | TotalR | AvgR | Worst | MaxDD |
|---|---:|---:|---:|---:|---:|---:|---:|
| Candidate A | 89 | 71.91% | 4.32 | +179.5R | +2.017R | -5R | 7R |

## Best high-quality addon candidate

Recommended addon candidate B:

```text
regime == MID_MIXED
AND trend_eff96 >= 0.633155
```

B-only result on A-rejected rows:

| Count | Win rate | PF | TotalR | Worst |
|---:|---:|---:|---:|---:|
| 32 | 71.88% | 3.50 | +30.0R | -3R |

B-only monthly:

| Month | Count | Win rate | PF | TotalR | Worst |
|---|---:|---:|---:|---:|---:|
| 2026-03 | 3 | 100.00% | inf | +4.0R | +1R |
| 2026-04 | 13 | 61.54% | 3.00 | +8.0R | -1R |
| 2026-05 | 14 | 78.57% | 4.00 | +18.0R | -3R |
| 2026-06 | 2 | 50.00% | 1.00 | 0.0R | -2R |

## Candidate A + Candidate B

| Policy | Count | Win rate | PF | TotalR | AvgR | Worst |
|---|---:|---:|---:|---:|---:|---:|
| Candidate A only | 89 | 71.91% | 4.32 | +179.5R | +2.017R | -5R |
| Candidate A + B | 121 | 71.90% | 4.17 | +209.5R | +1.731R | -5R |

Monthly Candidate A + B:

| Month | Count | Win rate | PF | TotalR | Worst |
|---|---:|---:|---:|---:|---:|
| 2026-03 | 56 | 75.00% | 5.36 | +96.0R | -3R |
| 2026-04 | 34 | 64.71% | 3.32 | +51.0R | -5R |
| 2026-05 | 28 | 75.00% | 3.78 | +55.5R | -5R |
| 2026-06 | 3 | 66.67% | 4.50 | +7.0R | -2R |

## Interpretation

This addon is a better fit than simply adding the largest rejected-row filter. Larger filters increased count but degraded win rate and PF too much.

Candidate B is a different vector from Candidate A:

```text
A: short-lookback top5 all-consensus stack permission
B: rejected MID_MIXED clusters with high trend efficiency, capped to CAP3
```

It specifically improves April and May count:

```text
April: 21 -> 34
May: 14 -> 28
```

While preserving about 72% win rate overall.

## Current recommendation

Use Candidate A as the main signal and Candidate B as a controlled addon candidate.

Do not runtime-approve yet.

Next validation:

```text
1. Apply A+B on all available folds/months with strict no-lookahead.
2. Confirm B was selected without using future April/May outcomes.
3. Compare A-only vs A+B by month, fold, regime, direction, and overlap.
```
