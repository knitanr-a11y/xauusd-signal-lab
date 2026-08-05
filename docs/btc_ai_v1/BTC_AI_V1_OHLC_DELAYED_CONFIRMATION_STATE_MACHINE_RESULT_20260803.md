# BTC AI V1 — OHLC Delayed-Confirmation State-Machine Forensic Result

Date: 2026-08-03  
Status: `COMPLETE_NO_DELAYED_CONFIRMATION_SUPPORT_SURVIVOR`

## Authority

- accepted XM `BTCUSD#` closed-bar OHLC only
- MT5 broker-server naive time
- development: 2024-01 through 2025-12, exactly 24 calendar months
- cross-fitted ordinary-M15 baseline from the accepted Stage 29 rerun
- no external or volume data
- no candidate PnL and no 2026 evaluation

## Purpose

Stage 29 found small post-anchor direction residual information but not enough for support. This forensic replaced a continuous score with a preregistered causal state machine and tested whether waiting for post-anchor confirmation creates stable incremental direction information.

Each anchor could enter each state once. First occurrence was determined over the full 2023–2025 sequence before filtering to 2024–2025, preventing boundary misclassification.

## States

Actionable:

1. `FAILED_ACCEPTANCE_RECLAIM` — reversal;
2. `DEEP_PULLBACK_AFTER_EXTENSION` — reversal;
3. `MATURE_EXTENSION` — reversal;
4. `SHALLOW_PULLBACK_AFTER_EXTENSION` — continuation;
5. `ACCEPTED_CONTINUATION` — continuation;
6. `ADVERSE_DOMINANT` — reversal.

Diagnostic only:

- `STALLED_NEAR_ANCHOR`;
- `EARLY_UNRESOLVED`;
- `OTHER`.

For continuation states, the effect is the ordinary-baseline residual in the anchor direction. For reversal states, its sign is reversed. Positive means improvement in the preregistered action direction relative to an ordinary state.

## Counts

- all first confirmation events: **95,440**;
- actionable events: **70,892**;
- diagnostic events: **24,548**;
- period: 24 calendar months;
- every actionable state active in 24/24 months;
- all six anchor families represented in every actionable state.

## Formal result

| State | Orientation | Events / 24m | Per month | Monthly min / median / max | Oriented residual | Bootstrap P(mean>0) | Pass |
|---|---|---:|---:|---:|---:|---:|---|
| failed acceptance / reclaim | reversal | 16,111 | 671.29 | 599 / 662.5 / 757 | **-0.0161** | 0.049 | no |
| deep pullback after extension | reversal | 17,417 | 725.71 | 633 / 730.5 / 831 | **-0.0103** | 0.146 | no |
| mature extension | reversal | 8,164 | 340.17 | 281 / 333.5 / 417 | +0.0081 | 0.726 | no |
| shallow pullback after extension | continuation | 8,528 | 355.33 | 290 / 360.5 / 401 | **-0.0107** | 0.160 | no |
| accepted continuation | continuation | 9,596 | 399.83 | 340 / 400 / 476 | **-0.0266** | 0.034 | no |
| adverse dominant | reversal | 11,076 | 461.50 | 390 / 462.5 / 533 | +0.0031 | 0.626 | no |

Formal support survivors: **0**.

All states passed density, active-month and family-diversity gates. All failed the frozen +0.08 mean-oriented-residual gate. No state was positive across all four half-years and all three D1 regimes.

## Findings

### Accepted continuation was not continuation confirmation

- 9,596 events / 24 months = 399.83/month;
- oriented residual -0.0266;
- negative in 2024H2, 2025H1 and 2025H2;
- negative in D1 DOWN, NEUTRAL and UP.

A close at least 0.5 ATR beyond the anchor with less than 0.25 ATR pullback was slightly worse than its ordinary-state expectation.

### Shallow pullback did not stabilize continuation

- 8,528 events / 24 months = 355.33/month;
- oriented residual -0.0107;
- only 2025H1 positive;
- all three D1 states negative.

### Reclaim through the anchor was not reversal confirmation

- 16,111 events / 24 months = 671.29/month;
- reversal-oriented residual -0.0161;
- three of four half-years negative;
- all D1 states negative.

### Deep pullback also failed

- 17,417 events / 24 months = 725.71/month;
- reversal-oriented residual -0.0103;
- only 2025H2 positive.

### Mature extension was the strongest reversal state but negligible

- 8,164 events / 24 months = 340.17/month;
- oriented residual +0.0081;
- bootstrap probability positive 0.7255;
- 2024H1 and D1 NEUTRAL negative.

The effect was below one percentage point versus the frozen eight-point requirement.

### Adverse-dominant was nearly neutral

- 11,076 events / 24 months = 461.50/month;
- oriented residual +0.0031;
- 2024H2 and D1 DOWN negative.

## Diagnostic states

| State | Events / 24m | Per month | Actual residual mean |
|---|---:|---:|---:|
| stalled near anchor | 1,390 | 57.92 | -0.0060 |
| early unresolved | 15,793 | 658.04 | +0.0070 |
| other | 7,365 | 306.88 | +0.0010 |

## Formal interpretation

`SIMPLE_DELAYED_CONFIRMATION_STATES_DO_NOT_CREATE_DIRECTIONAL_EDGE_BEYOND_CURRENT_OHLC_BASELINE`

The result rejects several intuitive fixes:

1. Waiting for price to remain outside the anchor is insufficient.
2. Waiting for a shallow pullback is insufficient.
3. A reclaim through the anchor is not a reliable reversal confirmation.
4. Deep pullback and mature extension do not create invariant reversal value.
5. Static ATR thresholds do not solve the time- and D1-dependent meaning shift.

## Conclusion

- support survivors: **0**;
- leave-group-out transfer: not opened;
- candidate PnL: not opened;
- 2026: not opened;
- supported candidates remain **0**.

No state definition, orientation, threshold, family, age or D1 condition was changed after outcomes.

## Next direction

The next distinct work should target the drift mechanism directly. Compare fixed expanding learning with 3-, 6- and 12-month rolling training and monthly recalibration, using the same OHLC targets. First test monthly label ordering and stability before any PnL grid. 2026 remains diagnostic-only.