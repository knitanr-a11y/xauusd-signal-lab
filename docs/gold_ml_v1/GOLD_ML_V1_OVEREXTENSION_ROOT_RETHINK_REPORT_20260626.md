# GOLD_ML_V1 overextension root redesign audit — 2026-06-26

Status: `ROOT_CAUSE_AUDIT_COMPLETE_REBUILD_REQUIRED_NO_PROMOTION`

## Root conclusion

The failure was not mainly caused by poor loss-filter deletion. The original architecture treated overextension as an immediate entry signal. In reality, overextension is only a setup that can continue, produce a short snapback, or become a full reversal.

The redesign separated:

1. M15 overextension setup onset;
2. M5 first reversal evidence;
3. second confirmation by holding the reversal side of EMA20 or by retest and re-break;
4. structural stop placement;
5. monthly rolling meta-gating.

## First-touch evidence

Within 12 hours after the first trigger:

- LONG: 76.5% eventually reached +1R MFE, but 79.2% also reached -1R MAE.
- SHORT: 81.8% reached +1R MFE, but 83.0% also reached -1R MAE.

The main problem is unstable first-touch order, not absence of eventual reversal movement.

## Best two-stage mechanical LONG

M15 overextension, M5 reversal, two closes held above EMA20, structural risk floor 1 ATR, target 0.75R, horizon 12 hours:

| Year | N | WR | PF |
|---:|---:|---:|---:|
| 2023 | 101 | 61.4% | 1.210 |
| 2024 | 118 | 61.0% | 1.201 |
| 2025 | 87 | 50.6% | 0.767 |
| 2026 diagnostic | 47 | 51.1% | 0.783 |

Two-stage confirmation improved entry quality, but the edge disappeared in 2025.

## Rolling causal meta-gate

At each month start, only fully resolved past events were used. The prior 120-day validation had to have at least 8 admitted trades, WR >= 60%, PF >= 2 and positive mean R; otherwise the next month was OFF.

| Direction | N | WR | PF | Total R |
|---|---:|---:|---:|---:|
| LONG | 35 | 65.7% | 1.529 | +5.966 |
| SHORT | 59 | 42.4% | 0.788 | -6.306 |

The rolling controller improved LONG selectivity, but did not reach PF2. SHORT remained invalid.

## Nonstationarity

A classifier using entry-known features distinguished 2023 LONG events from 2025 LONG events with mean 5-fold AUC 0.882. Important shifts included D1 EMA gap and slope, D1 RSI/ATR regime, M5 spread-to-ATR and confirmation waiting time.

Static loss zones are therefore expected to reverse across years.

## Decision

- Reject static loss pruning.
- Reject immediate overextension entry.
- Reject symmetric SHORT overextension.
- Keep the two-stage LONG logic as research-only.
- Future architecture must use setup survival, competing-risk TP/SL ordering, separate MFE/MAE prediction, dynamic payoff and rolling regime control.
- 2024–2026 are already exposed and cannot be reused as untouched holdout.
- Existing nine, root BAT, health gate, live, MT5 and Discord remain unchanged.
