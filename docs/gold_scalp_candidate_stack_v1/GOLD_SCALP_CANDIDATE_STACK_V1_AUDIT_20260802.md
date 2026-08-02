# GOLD SCALP CANDIDATE STACK V1 — Research Audit

Date: 2026-08-02  
Formal status: **`RETROSPECTIVE_CANDIDATE_STACK_CALIBRATION_PASS_FORWARD_FAIL_NO_FORMAL_PORTFOLIO`**

## User objective

Combine several lower-frequency candle-only scalping candidates instead of requiring one engine to produce at least 20 trades per month. Standard execution remained:

- standard spread 0.30 USD once;
- initial SL <= 5 USD;
- TP >= 5 USD;
- breakeven exits allowed;
- exact M1 resolution;
- one-position non-overlap across engines.

## Candidate families

The exact portfolio search allowed at most one candidate from each family:

1. event-direction anchored AI selection;
2. hierarchical high-confidence router;
3. false-break fade with event/H1/H4 support.

Same-entry collisions were resolved by a frozen quality-first or frequency-first priority. Trades were then made globally one-position non-overlap.

## V1 fixed-score candidate stack

The selected 2024H2 portfolio was:

- `EA_Q0.975_E0`;
- `HR_T0.5_D0.7_E0.7`;
- `FB_Q0.95_D1.5_W30_R10_TP7P5_SL3P5_H180_EVENT_MAJORITY_H1`;
- quality-first priority.

### 2024H2 calibration

- trades: 130;
- median monthly trades: 20.5;
- positive-PnL win rate: 55.38%;
- PF: 2.0562;
- net: +238.22 USD;
- DD: 23.91 USD;
- positive months: 6/6.

Family contributions after global overlap removal:

- event anchored: 63 trades, WR 53.97%, PF 1.8318;
- false break: 31 trades, WR 61.29%, PF 3.0049;
- hierarchical: 36 trades, WR 52.78%, PF 1.9034.

This proves that stacking sparse engines can satisfy the desired historical frequency and quality simultaneously.

### 2025+ exploratory evaluation

The same frozen portfolio failed:

- trades: 1,474;
- median monthly trades: 51;
- win rate: 32.50%;
- PF: 0.9189;
- net: -379.50 USD;
- DD: 515.31 USD.

The fixed absolute score thresholds admitted far more rows after 2025. The event-anchored component caused most of the loss.

## V1B causal 60-day rolling rank

Absolute scores were replaced by past-60-calendar-day percentile ranks, excluding the current MT5 date.

The closest 2024H2 portfolio produced:

- trades: 118;
- median monthly trades: 18;
- win rate: 51.69%;
- PF: 1.6277;
- net: +126.37 USD.

It failed the required 120 trades and 20 trades/month gate. Its exploratory 2025+ metrics were also negative:

- trades: 1,151;
- win rate: 34.49%;
- PF: 0.9551;
- net: -132.49 USD.

Rolling rank reduced score drift but did not preserve directional quality.

## False-break improvement attempts

### Semiannual expanding retraining

Four fixed false-break tiers were retrained at January/July boundaries using only fully resolved prior rows and then ranked over the past 60 days.

All four tiers had 2025+ PF below 1.0. The high-quality pair produced:

- 744 trades;
- median 27 trades/month;
- WR 31.45%;
- PF 0.8752;
- net -209.79 USD.

Retraining therefore did not rescue the family.

### Reclaim quality and retest filters

A separate structural pass tested:

- reclaim depth of 0 / 0.25 / 0.50 USD;
- reclaim-bar body fraction;
- maximum overshoot;
- immediate entry versus reference retest;
- signal cooldown;
- event and H1/H4 support.

No row met the fixed sparse-candidate gate of at least 20 trades, median 3/month, WR >=55%, PF >=1.8 and four positive months.

The highest descriptive row reached 9 trades, WR 77.78% and PF 5.24, but occurred in only two positive months. Increasing win rate again collapsed the frequency too far.

## Existing candidate catalog worth retaining

These earlier event-first candidates remain useful as frozen prospective observations, not as a proven combined historical portfolio:

- M5 gap-fill LONG + logistic TP5/SL3: calibration 23 trades, WR 56.52%, PF 1.2068; 2025+ 26 trades, WR 57.69%, PF 2.1623.
- Daily-reopen gap-down reclaim LONG + logistic TP5/SL3: calibration 13 trades, WR 76.92%, PF 3.2073; 2025+ 28 trades, WR 50.00%, PF 1.6363.
- Daily-reopen gap-down reclaim LONG + small LightGBM TP5/SL3: calibration 13 trades, WR 76.92%, PF 2.7385; 2025+ 16 trades, WR 68.75%, PF 3.4407. The user correctly rejected this as too small for adoption.

Their exact combined performance is not claimed here because their complete trade ledgers were not part of the current stack cache and historical selection has already been repeated extensively.

## Decision

`NO_FORMAL_PORTFOLIO`

Candidate stacking is retained as the correct architecture, but historical selection cannot establish a stable portfolio. The correct next use is a frozen candidate catalog with exact no-backfill prospective recording. New candle-only candidates may be added only as independently preregistered engines; historical thresholds must not be re-optimized to force a combined pass.

No Shadow, Discord, MT5 order, live trading, promotion, or merge authorization follows from this audit. Frozen V19 and Challenger C1 were not modified.