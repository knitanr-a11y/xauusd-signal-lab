# GOLD V2 Phase3 lookback-window validation

Created: 2026-06-03
Status: audit-only / not runtime approved

## Purpose

The user correctly pointed out that thresholds should not simply be fixed forever. However, the more important question is how much historical data should be used to choose the thresholds.

This audit tests lookback windows:

```text
1 month
2 months
3 months
4 months
5 months
6 months
expanding
```

For each fold, the policy is selected only from the prior lookback window, then applied to the next test month.

## Source

```text
WF_REBUILD_TOP2_PER_ORIGIN clusters with regime/features
Test months: 2026-03, 2026-04, 2026-05, 2026-06
Rows in aggregate test: 351
```

Policy family:

```text
CAP3 fixed
uncapped fixed
count-based stacking
count-based stacking with selected risk caps
Phase3 exact rubric
```

Selectors tested:

```text
total_penalty
pf_balance
tail_limited
```

## Key finding

The lookback length itself was not the dominant issue.

When the selection objective is too TotalR-oriented, almost every lookback selects uncapped or count>=4-style stacking. That keeps TotalR higher than CAP3, but it also keeps the -11R tail.

Therefore, the next improvement must not be only variable lookback. It must include explicit tail-risk constraints in the selection objective.

## Aggregate comparison

On the same 351 aggregate test rows:

| View | Count | Win rate | PF | TotalR | Worst | Max month DD |
|---|---:|---:|---:|---:|---:|---:|
| fixed CAP3 | 351 | 58.97% | 1.85 | +180.5R | -3.0R | 10.0R |
| fixed uncapped | 351 | 58.69% | 1.96 | +227.5R | -11.0R | 18.0R |
| Phase3 exact fixed | 351 | 59.26% | 2.10 | +234.5R | -5.0R | 12.0R |
| dynamic lookback best observed | 351 | 58.69% | 1.96 | +227.5R | -11.0R | 18.0R |

Best observed dynamic setting:

```text
lookback = 3 months
selector = pf_balance
TotalR = +227.5R
PF = 1.96
Worst = -11R
```

This did not beat the fixed Phase3 exact rubric.

## Lookback summary for dynamic selection

| Lookback | Selector | Count | PF | TotalR | Worst | Max month DD |
|---|---|---:|---:|---:|---:|---:|
| 3 | pf_balance | 351 | 1.96 | +227.5R | -11.0R | 18.0R |
| 1 | pf_balance | 351 | 1.93 | +220.0R | -11.0R | 18.0R |
| 2 | pf_balance | 351 | 1.92 | +219.0R | -11.0R | 18.0R |
| expanding | pf_balance | 351 | 1.92 | +218.0R | -11.0R | 18.0R |
| 1 | total_penalty | 351 | 1.96 | +227.5R | -11.0R | 18.0R |
| 3 | total_penalty | 351 | 1.96 | +227.5R | -11.0R | 18.0R |
| expanding | total_penalty | 351 | 1.96 | +227.5R | -11.0R | 18.0R |

## Interpretation

A 3-month lookback was slightly best under the pf_balance selector, but the difference versus 1-6 months was small.

The larger issue is that the dynamic selector keeps choosing uncapped-like policies when past uncapped TotalR is strong. That means it fails to prevent the exact tail-risk problem we care about.

## Recommendation

Do not just vary thresholds by lookback.

Use a two-layer process:

```text
Layer 1: choose a lookback window, likely 3 months as initial candidate.
Layer 2: enforce hard tail-risk constraints during selection.
```

Candidate hard constraints:

```text
selected policy worst_loss must be no worse than CAP3 worst - 3R, or absolute worst >= -5R
selected policy max drawdown must not exceed CAP3 max drawdown by more than 30%-50%
selected policy must improve CAP3 TotalR by a minimum margin, e.g. +10R or +15%
```

Without these constraints, the optimizer tends to rediscover uncapped stacking.

## Current decision

```text
Best default baseline: fixed CAP3
Best fixed experimental rubric: Phase3 exact
Best lookback candidate: 3 months, but only if paired with tail-risk constraints
AI API: not needed for this numeric rubric
Runtime approval: not yet
```
