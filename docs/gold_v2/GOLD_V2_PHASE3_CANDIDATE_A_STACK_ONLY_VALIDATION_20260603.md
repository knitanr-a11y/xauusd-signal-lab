# GOLD V2 Phase3 Candidate A stack-only gate validation

Created: 2026-06-03
Status: audit-only / not runtime approved

## Candidate A definition

Candidate A uses the best sub-monthly dynamic stack policy from the prior audit:

```text
lookback = 10 days
selector = tail_hard
topN = 5
vote_mode = all consensus
```

Instead of keeping every cluster and falling back to CAP3, Candidate A only keeps clusters where all five selected policies agree that stacking is allowed.

```text
all five agree -> keep and use stacked_same_direction_profit_r
otherwise -> reject / no trade
```

This is a trade-entry gate, not just a stack-size controller.

## Aggregate result on 2026-03 to 2026-06 test set

| View | Count | Win rate | PF | TotalR | AvgR | Worst | MaxDD | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fixed CAP3 all 351 | 351 | 58.97% | 1.85 | +180.5R | +0.514R | -3.0R | 10.0R | 4 |
| fixed uncapped all 351 | 351 | 58.69% | 1.96 | +227.5R | +0.648R | -11.0R | 18.0R | 4 |
| Candidate A kept uncapped | 89 | 71.91% | 4.32 | +179.5R | +2.017R | -5.0R | 7.0R | 2 |
| Candidate A kept but CAP3-sized | 89 | 71.91% | 3.27 | +116.0R | +1.303R | -3.0R | 7.0R | 3 |

## Monthly result

| Month | Kept | Total clusters | Rejected | Win rate | PF | TotalR | AvgR | Worst | MaxDD | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-03 | 53 | 143 | 90 | 73.58% | 5.18 | +92.0R | +1.736R | -3.0R | 3.0R | 1 |
| 2026-04 | 21 | 116 | 95 | 66.67% | 3.39 | +43.0R | +2.048R | -5.0R | 7.0R | 2 |
| 2026-05 | 14 | 87 | 73 | 71.43% | 3.68 | +37.5R | +2.679R | -5.0R | 5.0R | 1 |
| 2026-06 | 1 | 5 | 4 | 100.00% | inf | +7.0R | +7.000R | +7.0R | 0.0R | 0 |

March to May only:

```text
kept trades: 88
monthly pace: about 29.3 trades/month
win rate: about 71.6%
PF: above 4.0
```

## Interpretation

Candidate A substantially reduces trade count while preserving most of fixed CAP3 TotalR.

It converts:

```text
351 candidate clusters -> 89 kept trades
about 100/month -> about 25-30/month
```

This is closer to a practical notification/trade frequency.

The trade-off is that TotalR drops versus uncapped all-cluster trading, but quality improves sharply:

```text
win rate: 58.69% uncapped all -> 71.91% Candidate A
PF: 1.96 uncapped all -> 4.32 Candidate A
worst: -11R uncapped all -> -5R Candidate A
maxDD: 18R uncapped all -> 7R Candidate A
```

## Key caveat

Candidate A should not be runtime-approved yet.

This validation still uses the same 2026-03 to 2026-06 test universe used in the sub-monthly audit. It is a strong candidate, but it still needs:

```text
1. strict walk-forward implementation audit
2. no look-ahead check for candidate selection
3. comparison against BTC-style reusable pipeline if reused
4. runtime guard design
```

## Current recommendation

Use Candidate A as the leading deterministic gate candidate.

Do not use free AI judgement.

Next step:

```text
Implement Candidate A as audit-only deterministic evaluator and replay it with monthly/fold reports.
```
