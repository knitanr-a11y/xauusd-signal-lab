# GOLD V2 ABC strict validation

Created: 2026-06-03
Status: audit-only / not runtime approved
Corrected: 2026-06-03 - corrected ABC fixed counts and clarified train_rows meaning.

## Correction note

Two issues were corrected after review:

1. `train_rows` in the B/C train-viability tables means the number of historical train clusters available before that test month. It is not the number of trades in the test month. For example, the 2026-06 row has only 5 test clusters, but 768 historical train clusters available before June.
2. The fixed ABC aggregate count in the strict-validation output is 123, not 125. The previous 125 number came from an earlier probe file. The strict validation ledger excludes zero/neutral rows from the aggregate count metrics.

## Scope note

Candidate A is no-lookahead: its top5 policies are selected per fold from the prior 10-day training window and then applied to the test month.

Candidate B and Candidate C were discovered after reviewing the current audit set. Therefore:

```text
A+B+C fixed on 2026-03 to 2026-06 = frozen-rule replay / strong candidate result
C selected automatically from each training fold = stricter no-lookahead selection stress test
```

The distinction matters. Fixed C performs very well, but a naive train-selected C over-selects and degrades.

## Fixed ABC rules

A:

```text
10-day lookback / top5 all-consensus / stack-only
profit = stacked_same_direction_profit_r
```

B:

```text
not A
AND regime == MID_MIXED
AND trend_eff96 >= 0.633155
AND RR >= 1.5
profit = stacked_capped3_profit_r
```

C:

```text
not A
AND not B
AND range96 >= 100.42
AND range96 <= 117.86
profit = stacked_capped3_profit_r
```

## Aggregate comparison

| View | Count | Win rate | PF | TotalR | AvgR | Worst | Max month DD | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A only | 89 | 71.91% | 4.32 | +179.5R | +2.017R | -5R | 7R | 2 |
| A+B(RR>=1.5) | 99 | 71.72% | 4.39 | +196.5R | +1.985R | -5R | 5R | 1 |
| A+B+C fixed | 123 | 74.80% | 4.58 | +225.5R | +1.833R | -5R | 6R | 2 |
| fixed CAP3 all | 351 | 58.97% | 1.85 | +180.5R | +0.514R | -3R | 10R | 4 |
| fixed uncapped all | 351 | 58.69% | 1.96 | +227.5R | +0.648R | -11R | 18R | 4 |
| train-selected C naive | 329 | 58.97% | 2.15 | +234.5R | +0.713R | -5R | 15R | 4 |

## Monthly fixed A+B+C

| Month | Count | Win rate | PF | TotalR | Worst | MaxDD | Signals |
|---|---:|---:|---:|---:|---:|---:|---|
| 2026-03 | 58 | 75.86% | 5.52 | +99.5R | -3R | 3R | A:53 / B:1 / C:4 |
| 2026-04 | 34 | 70.59% | 3.83 | +56.5R | -5R | 6R | A:21 / B:3 / C:10 |
| 2026-05 | 29 | 75.86% | 3.88 | +60.5R | -5R | 5R | A:14 / B:6 / C:9 |
| 2026-06 | 2 | 100.00% | inf | +9.0R | +2R | 0R | A:1 / C:1 |

## Signal breakdown in fixed ABC

| Signal | Count | Win rate | PF | TotalR | AvgR | Worst | MaxDD |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 89 | 71.91% | 4.32 | +179.5R | +2.017R | -5R | 7R |
| B(RR>=1.5) | 10 | 70.00% | 5.25 | +17.0R | +1.700R | -3R | 3R |
| C fixed | 24 | 87.50% | 6.80 | +29.0R | +1.208R | -3R | 3R |

## Train viability of fixed B/C

Fixed B and C also looked reasonable inside prior train windows, which supports them as candidates but does not prove runtime safety.

Important: `train_rows` below is the historical training-cluster count available before the test month. It is not the number of trades in that test month. The test-month counts are shown in the monthly table above.

C fixed train performance by fold:

| Test month | Historical train rows | C count inside train | Win rate | PF | TotalR | Worst |
|---|---:|---:|---:|---:|---:|---:|
| 2026-03 | 271 | 19 | 84.21% | 8.83 | +23.5R | -1R |
| 2026-04 | 442 | 19 | 68.42% | 2.58 | +9.5R | -2R |
| 2026-05 | 570 | 39 | 79.49% | 6.13 | +41.0R | -1R |
| 2026-06 | 768 | 68 | 64.71% | 2.41 | +53.5R | -3R |

B fixed train performance by fold:

| Test month | Historical train rows | B count inside train | Win rate | PF | TotalR | Worst |
|---|---:|---:|---:|---:|---:|---:|
| 2026-03 | 271 | 8 | 62.50% | 3.33 | +7.0R | -1R |
| 2026-04 | 442 | 8 | 87.50% | 7.25 | +12.5R | -2R |
| 2026-05 | 570 | 23 | 60.87% | 2.64 | +18.0R | -2R |
| 2026-06 | 768 | 6 | 100.00% | inf | +11.0R | +1R |

## Naive train-selected C stress test

When C is selected automatically from each training fold using a broad filter search, it over-selects:

| Month | Count | Win rate | PF | TotalR | Worst | MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| 2026-03 | 133 | 63.16% | 2.98 | +115.0R | -3R | 5.5R |
| 2026-04 | 114 | 57.89% | 2.16 | +74.5R | -5R | 11R |
| 2026-05 | 77 | 54.55% | 1.59 | +44.0R | -5R | 15R |
| 2026-06 | 5 | 40.00% | 1.13 | +1.0R | -3R | 6R |

Aggregate:

```text
329 trades / 58.97% WR / PF 2.15 / +234.5R / MaxDD 15R
```

This shows that automated C discovery must be constrained. The fixed C range band is much cleaner than broad train-selected C.

## Judgement

A+B+C fixed is the best practical composition so far in this audit set:

```text
123 counted trades
74.80% win rate
PF 4.58
+225.5R
Worst -5R
Max month DD 6R
```

However, C was found after inspecting rejected rows. Do not call it runtime-approved yet.

## Next required step

Freeze A+B+C as a candidate specification and test it on the next truly unseen period, or rerun historical candidate discovery using only prior train windows with a much narrower C-family.

Recommended status:

```text
Candidate A: main signal candidate
Candidate B(RR>=1.5): acceptable addon candidate
Candidate C fixed range96 band: very promising but needs frozen forward validation
AI API: not needed
Runtime approval: not yet
```
