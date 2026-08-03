# BTC AI V1 — OHLC 2026 Failure Root-Cause Forensic

Date: 2026-08-03  
Status: `COMPLETE_ROOT_CAUSE_IDENTIFIED_NO_RESCUE`

## Scope

This forensic uses only the accepted XM `BTCUSD#` closed-bar history and exact M1 execution. No Binance, funding, open-interest, order-flow or other external data is used.

It explains why five second-cycle SHORT finalists were profitable in 2024–2025 but failed in 2026-01 through 2026-07. It does not select a new filter, modify a threshold, rescue a candidate or authorize trading.

## 1. SHORT opportunity did not disappear

The 1 ATR stop / 1.5 ATR target-before-stop SHORT label rate was:

| Period | Calendar months | SHORT-positive rate |
|---|---:|---:|
| 2024H1 | 6 | 33.51% |
| 2024H2 | 6 | 35.52% |
| 2025H1 | 6 | 35.77% |
| 2025H2 | 6 | 36.81% |
| 2026-01 to 2026-07 | 7 | 36.53% |

Therefore the failure is not explained by a lack of downside movement or a disappearance of generic SHORT opportunities.

## 2. The OHLC regime changed materially

Across all valid M15 decision points:

| OHLC state | 2024–2025, 24m | 2026-01 to 2026-07, 7m |
|---|---:|---:|
| D1 uptrend share | 44.60% | 15.10% |
| D1 neutral share | 29.69% | 38.20% |
| D1 downtrend share | 25.71% | 46.69% |
| H1/H4/D1 all-up share | 19.19% | 5.40% |
| H1/H4/D1 all-down share | 8.30% | 18.45% |
| mean D1 EMA20 slope / ATR | +0.1243 | -0.1232 |
| mean H4 EMA20 slope / ATR | +0.0664 | -0.0433 |

The strongest feature drift was daily trend geometry. `d1_ema20_slope4_atr` had PSI 1.4414, far above every other feature.

## 3. The selected-event geometry changed from a pullback/impulse to a mature selloff

For completed finalist trades, candidate-trade weighted means changed as follows:

| OHLC-derived event feature | 2024–2025 | 2026 | Interpretation |
|---|---:|---:|---|
| mean D1 trend state | +0.654 | -0.052 | events moved from structurally bullish to mixed/down |
| D1 EMA20 slope / ATR | +0.434 | +0.037 | strong higher-timeframe rise largely disappeared |
| one-bar return / ATR | -0.191 | -0.493 | entry followed a much sharper immediate fall |
| 32-bar return / ATR | -0.150 | -1.154 | entry occurred much deeper into an established fall |
| distance from EMA50 / ATR | -0.280 | -0.876 | price was much farther below medium trend |
| rolling-20 position | 0.485 | 0.367 | entry was closer to the lower end of its recent range |
| range expansion / rolling median | 2.31 | 2.91 | entry candle sequence was more expanded/exhausted |
| candle range / ATR | 1.30 | 1.70 | entry occurred after larger directional candles |

The same score threshold therefore captured a different OHLC object:

- 2024–2025: a bearish impulse or correction while the higher-timeframe structure was often still rising;
- 2026: a deeper, faster and more expanded decline, frequently after much of the move had already occurred.

This is consistent with late SHORT entry and rebound risk rather than early continuation entry.

## 4. What the finalist models had actually learned

The three MTF finalist definitions used logistic models. Their largest standardized coefficients included:

- negative M15 EMA20 slope;
- negative H1 EMA20 slope;
- negative one-bar return;
- positive H1 trend state;
- positive D1 trend state;
- positive RSI and ATR-ratio terms.

Thus the profitable historical pattern was not a generic downtrend SHORT. It was closer to:

> short-term bearish acceleration occurring inside a still-positive or mixed higher-timeframe structure.

In 2026, negative short-term acceleration occurred far more often inside an already bearish and extended structure. The additive model could assign a similar score, but the post-entry meaning was different.

## 5. Score distribution looked stable while predictive ordering collapsed

Score PSI between 2025H2 calibration and 2026 was only approximately 0.007–0.009. The score means and P95 values therefore looked superficially stable.

However AUC fell:

| Finalist model group | Calibration AUC | 2026 AUC |
|---|---:|---:|
| MTF logistic candidates | 0.5252–0.5257 | 0.5080–0.5088 |
| Full-causal logistic candidates | 0.5402 | 0.5232 |

For the MTF models, the highest score decile had a 2026 SHORT-label rate of only approximately 34.5–34.7%, below the unconditional 36.53% SHORT-label rate.

Four of five frozen event sets had hit rates below the unconditional 2026 SHORT-label rate. The model continued to emit high scores, but those scores no longer ordered the good SHORT opportunities.

This is conditional-relation or concept drift, not merely a change in score scale.

## 6. Static D1 filtering alone does not explain or fix the failure

Candidate-trade weighted development results by D1 state were:

| D1 state | Trades | PF | Net |
|---|---:|---:|---:|
| D1 up | 2,693 | 1.2458 | +158,499.26 |
| D1 neutral | 689 | 1.0707 | +14,746.44 |
| D1 down | 292 | 1.0676 | +6,340.25 |

The historical edge was overwhelmingly concentrated in D1-up conditions.

But composition change alone is insufficient. Applying the 2024–2025 average PnL within each D1 state to the actual 2026 D1-state trade counts would have predicted approximately **+45,765 USD** across the five candidate ledgers. Actual 2026 result was approximately **-70,522 USD**. The residual conditional deterioration was approximately **-116,287 USD**.

Therefore:

- fewer D1-up conditions contributed to the loss;
- the larger problem was that performance deteriorated inside the same coarse D1 categories;
- a simple post-result `D1 up only` filter is not an adequate causal explanation and is not authorized as a rescue.

## 7. Exact execution path deteriorated

### Main MTF 2R candidates

For `ML2_090`, `ML2_126` and `ML2_127`:

- development win rate: approximately 42.3–42.4%;
- 2026 win rate: approximately 36.3–37.1%;
- development TP rate: approximately 22.3–23.2%;
- 2026 TP rate: approximately 18.9–19.8%;
- development SL rate: approximately 47.5%;
- 2026 SL rate: approximately 57.3–58.4%.

Average favorable excursion weakened slightly, while average adverse excursion worsened by roughly 0.09–0.10 stop-R. The important change was not that price never moved favorably; it was that adverse movement and stop-first resolution became substantially more common.

### Other finalists

- `ML2_104`: TP rate fell from 37.17% to 30.32%; SL rate rose from 62.52% to 69.29%.
- `ML2_106`: equal-R win rate fell from 53.87% to exactly 50.00%.

The historical PF range of 1.17–1.21 was a relatively thin edge. A five-to-seven percentage-point deterioration in resolution rates was sufficient to reverse it.

## 8. Fixed spread contributed but was not the primary cause

Average fixed-spread burden increased because absolute M15 ATR was lower at finalist events:

- development: spread / ATR approximately 0.062–0.075;
- 2026: approximately 0.087–0.096.

A zero-spread counterfactual on the same frozen events showed:

| Candidate | 2026 PF at zero spread | 2026 net at zero spread |
|---|---:|---:|
| `ML2_090` | 0.8295 | -14,083.27 |
| `ML2_104` | 0.9283 | -2,872.09 |
| `ML2_106` | 1.1047 | +2,198.46 |
| `ML2_126` | 0.8595 | -11,231.28 |
| `ML2_127` | 0.8750 | -11,713.84 |

Four of five candidates still lost without spread. The 22.50 USD cost worsened the result and pushed the marginal `ML2_106` below break-even, but it did not create the broad failure.

## 9. Monthly timing of the collapse

Candidate-ledger weighted monthly PF in 2026 was:

| Month | PF | Net |
|---|---:|---:|
| January | 0.879 | -8,848.90 |
| February | 0.560 | -18,512.39 |
| March | 0.640 | -17,373.97 |
| April | 0.630 | -18,889.23 |
| May | 0.963 | -1,899.14 |
| June | 0.662 | -13,262.38 |
| July | 1.322 | +8,264.43 |

The failure was broad across the first six months, not one isolated shock month. July recovered, showing that the edge relationship was state-dependent rather than permanently impossible.

## 10. Why previous robustness tests did not catch it

The candidates passed:

- month-block bootstrap;
- matched-random controls;
- pseudo-state controls;
- parameter-neighborhood checks;
- entry-delay diagnostics.

These controls were useful against sampling noise, random timing and fragile parameters, but they all operated inside the 2024–2025 development environment. They did not test transfer into a regime where:

- daily trend composition reversed;
- selected events occurred later in the bearish path;
- the conditional meaning of the same score changed.

The prior methodology proved repeatability **within the observed regime**, not invariance across OHLC state transitions.

## Root-cause conclusion

`OHLC_STATE_TRANSITION_AND_CONDITIONAL_MEANING_SHIFT_CAUSED_LATE_SHORT_SELECTION`

The best-supported explanation is:

1. the models learned short-term bearish acceleration inside a predominantly rising or mixed higher-timeframe structure;
2. 2026 supplied far more bearish, extended and range-expanded structures;
3. the same additive score mapped those mature selloffs to high SHORT probability;
4. high scores therefore became late entries with higher stop-first and rebound risk;
5. fixed cost amplified the damage but was secondary;
6. existing robustness tests did not test regime-transfer invariance.

## Research implication

The next OHLC-only research must not start by adding more generic models. It must first represent **where a candle sequence is inside its state transition**:

- early impulse versus mature extension;
- pullback versus continuation versus exhaustion;
- slope acceleration versus deceleration;
- distance travelled since causal swing or range break;
- range expansion followed by acceptance or rejection;
- higher-timeframe phase interactions, not only static trend signs;
- leave-one-regime-out and regime-transition holdouts.

2026 remains diagnostic and cannot become an untouched support period. No new filter, candidate, Shadow, Discord or order authorization is created by this forensic.
