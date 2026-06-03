# GOLD V2 Phase3 sub-monthly lookback validation

Created: 2026-06-03
Status: audit-only / not runtime approved

## Purpose

The user asked whether lookback should be shorter than one month and whether multiple candidate policies should be used instead of a single winner.

This audit tests sub-monthly lookbacks and multi-candidate voting.

## Windows tested

```text
3 days
5 days
7 days
10 days
14 days
21 days
28 days
```

## Candidate selection

For each test fold/month:

1. Use only the most recent N days from the training period.
2. Score candidate stack policies on that short window.
3. Select top-N policies.
4. Apply them to the next test month using one of:
   - top1
   - any
   - majority
   - all consensus

## Baselines on the same 351 test rows

| Policy | Count | Win rate | PF | TotalR | Worst | Max month DD |
|---|---:|---:|---:|---:|---:|---:|
| fixed CAP3 | 351 | 58.97% | 1.85 | +180.5R | -3.0R | 10.0R |
| fixed uncapped | 351 | 58.69% | 1.96 | +227.5R | -11.0R | 18.0R |
| Phase3 exact fixed | 351 | 59.26% | 2.10 | +234.5R | -5.0R | 12.0R |

## Best sub-monthly result

Best risk-constrained result:

```text
lookback = 10 days
selector = tail_hard or total_penalty
topN = 5
vote_mode = all consensus
```

Performance:

```text
Count: 351
Win rate: 58.97%
PF: 2.13
TotalR: +244.0R
Worst: -5.0R
Max month DD: 12.0R
Max monthly loss streak: 4
```

This beats:

```text
fixed CAP3: +180.5R / PF 1.85 / worst -3R
fixed uncapped: +227.5R / PF 1.96 / worst -11R
Phase3 exact fixed: +234.5R / PF 2.10 / worst -5R
```

## Top sub-monthly configurations

| Lookback | Selector | TopN | Vote | PF | TotalR | Worst | Max month DD |
|---:|---|---:|---|---:|---:|---:|---:|
| 10d | tail_hard | 5 | all | 2.13 | +244.0R | -5.0R | 12.0R |
| 10d | total_penalty | 5 | all | 2.13 | +244.0R | -5.0R | 12.0R |
| 14d | tail_hard | 5 | all | 2.13 | +244.0R | -5.0R | 12.0R |
| 14d | total_penalty | 5 | all | 2.13 | +244.0R | -5.0R | 12.0R |
| 10d | pf_balance | 5 | all | 2.15 | +243.0R | -5.0R | 11.0R |
| 14d | pf_balance | 5 | all | 2.15 | +243.0R | -5.0R | 11.0R |
| 3d | pf_balance | 10 | all | 2.13 | +241.5R | -5.0R | 12.0R |

## Interpretation

Shorter than one month is viable, but not as a single best policy.

The stable pattern is:

```text
short lookback 10-14 days
select top 5 candidate policies
allow stacking only when all 5 agree
```

This avoids the worst behavior of a short lookback, where a single top policy overreacts to a tiny recent sample.

## Recommendation

The next candidate for deterministic validation should be:

```text
lookback = 10 days and 14 days
candidate_count = top 5
vote_mode = all consensus
risk selector = tail_hard / pf_balance
```

Do not use `any` voting for runtime. It is too permissive and tends to reintroduce uncapped tail risk.

## Runtime status

```text
AI API: not needed
MT5 order_send: disabled
Discord send: disabled
dispatch_ready: false
runtime approval: not yet
```
