# BTC AI V1 — Stage 32 drift attribution and rank stability result

Date: 2026-08-04

Formal status:

`BTC_AI_V1_HARD_WINDOW_SAMPLE_LOSS_AND_PAST_VISIBLE_RANK_INSTABILITY_NO_SUPPORTED_LIVE_DRIFT_GATE`

## Scope and causal audit

- authoritative XM `BTCUSD#` closed-bar OHLC only;
- period: 2024-01 through 2025-12, exactly 24 months;
- validation score/rank comparisons: 144;
- past-only calibration model-disagreement comparisons: 144;
- calibration rows at or after current refit month: 0;
- labels used to build past-only disagreement diagnostics: no;
- 2026 used: no;
- candidate PnL opened: no.

## Main measurements

| Schedule | Direction | Train rows / expanding | Past-only score rho | Past-only P90 Jaccard | Validation score rho | Validation P90 Jaccard | Rolling-only minus expanding-only label rate |
|---|---|---:|---:|---:|---:|---:|---:|
| ROLLING_12M | LONG | 0.562 | 0.685 | 0.414 | 0.611 | 0.305 | +0.0044 |
| ROLLING_12M | SHORT | 0.562 | 0.721 | 0.385 | 0.645 | 0.267 | -0.0720 |
| ROLLING_3M | LONG | 0.141 | 0.475 | 0.224 | 0.260 | 0.084 | +0.0131 |
| ROLLING_3M | SHORT | 0.141 | 0.489 | 0.222 | 0.286 | 0.104 | -0.0715 |
| ROLLING_6M | LONG | 0.281 | 0.546 | 0.279 | 0.380 | 0.128 | -0.0104 |
| ROLLING_6M | SHORT | 0.281 | 0.572 | 0.271 | 0.422 | 0.147 | -0.0558 |

## Attribution

1. **Material sample loss is real.** Average training-row ratios were about 0.141 for 3M, 0.281 for 6M and 0.562 for 12M.
2. **Rank instability is already observable before the validation month.** On the previous complete calendar month, rolling-versus-expanding score Spearman ranged from 0.475 to 0.721 and P90 Jaccard from 0.222 to 0.414.
3. **Instability increases in the validation month.** Validation P90 Jaccard fell to 0.084–0.305.
4. **SHORT reordering is harmful.** Rolling-exclusive SHORT selections had realized label rates lower than expanding-exclusive selections by approximately 5.6–7.2 percentage points across all windows.
5. **Sample loss is not a sufficient causal explanation.** The month-level relation between training-row loss and AUC delta was weak and changed sign by schedule/direction.
6. **No past-only diagnostic supports a live gate.** The largest absolute lagged Spearman with next-month AUC/lift delta was 0.372; signs were not stable across schedules, directions and targets.

## Formal conclusion

Hard-window adaptation discards too much history and produces a different ranking before future outcomes are known. This explains why hard rolling can fail, especially on SHORT. However, the permitted live-computable diagnostics do not reliably identify in advance which future month would benefit from rolling.

Therefore Stage 32 does **not** authorize:

- a drift gate;
- a direction-specific rescue;
- a schedule switch;
- candidate PnL;
- 2026 diagnosis;
- Shadow, Discord, MT5 orders, live-ready or final signal.

## Next research

`BTC_AI_V1_OHLC_SOFT_RECENCY_WEIGHTING_FORENSIC`

The next test keeps the expanding history but applies frozen exponential recency weights, directly separating adaptation from hard sample deletion. It remains ordering-only and 2024–2025 prequential before any PnL.
