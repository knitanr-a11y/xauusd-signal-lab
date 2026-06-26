# GML1-MLR1 Stage ML-00 — machine-learning design contract

Date: 2026-06-27  
Status: `DESIGN_CONTRACT_FROZEN_AUDIT_ONLY`

Machine-readable authority:

`config/gold_ml_v1/mlr1_stage_ml00_design_contract_20260627.json`

## 1. Purpose

`GML1-MLR1` is a new machine-learning research lane for GOLD_ML_V1.

It does not reproduce or continue the old Stage2 model. Old model weights, scalers, thresholds and feature lists are not reused. The current accumulated and Research WATCH candidates remain unchanged and are not used as MLR1-v1 input features.

This stage creates the contract only. It does not train a model or activate any signal.

## 2. Fixed raw development snapshot

MLR1-v1 development is restricted to the exact M1/M15/H1/H4/D1 files and SHA256 hashes recorded in the JSON contract.

Any new rows outside this snapshot are reserved for future shadow or prospective evaluation. They must not be merged back into MLR1-v1 training, feature selection, calibration or threshold selection.

A retrained model must be a new immutable version such as MLR1-v2.

## 3. Time and causality

- CSV `time` is MT5 server bar-open time.
- The latest CSV row is closed by contract.
- Every eligible closed M15 bar is a decision point.
- M15 decision time is M15 open time plus 15 minutes.
- An exact M1 bar at the decision time is mandatory. Missing exact M1 means skip.
- H1/H4/D1 features use only bars whose close time is at or before the decision time.
- No future bars, open higher-timeframe bars, next-M1 fallback or JST conversion are allowed in v1.

## 4. Primary label

Label ID:

`MLR1_LABEL_6H_TP1P5_SL1P0_ATR14`

For LONG and SHORT separately:

- ATR: M15 Wilder ATR14 using the current closed M15 decision bar.
- Target: 1.50 ATR.
- Protective distance: 1.00 ATR.
- Maximum horizon: six wall-clock hours.
- Outcomes: TARGET, PROTECTIVE or TIME.
- Same-M1 target/protective collision: protective first.
- TIME exit: last available M1 close at or before the horizon; never use a bar after it.
- Continuous target: realized gross R.

Raw OHLC is treated as bid. LONG enters at ask and exits/touches on bid. SHORT enters at bid and exits/touches on reconstructed ask.

Changing ATR period, target, protective distance, horizon, price-side handling or collision priority creates a new label ID and a new MLR version.

## 5. Cost policy

- Base: actual dynamic spread, no added slippage.
- Strong: 2x dynamic spread plus adverse 0.10 USD-price at entry and exit.
- Extreme: 3x dynamic spread plus adverse 0.20 USD-price at entry and exit.

Model and policy selection use Strong cost. Extreme cost is a required survival review.

## 6. Features

The first model is tabular. It uses a causal snapshot at each M15 decision.

Allowed families include normalized returns, candle structure, EMA gaps/slopes, ATR ratios and percentile, RSI, ADX, normalized MACD, Bollinger width, prior completed-day/week distances, spread/ATR, tick-volume ratios, MT5 server hour and weekday.

Not allowed in v1:

- absolute XAUUSD price,
- future-confirmed or repainting ZigZag/swing values,
- open H1/H4/D1 bars,
- current-bar-inclusive historical ranks or extrema,
- candidate event flags,
- missing-history imputation or warmup bridge.

Indicators may include the current closed M15 decision bar. Historical percentile/rank/extrema baselines must exclude the current bar using shift(1).

## 7. Model ladder

1. Unconditional outcome and mean-R baselines.
2. Always-LONG and always-SHORT execution baselines.
3. Regularized logistic/multinomial classification and linear expected-R regression.
4. Histogram gradient-boosting classification and regression.
5. TCN/LSTM only after tabular models pass the frozen gate and only when they add material walk-forward value.

LONG and SHORT models, calibration and diagnostics are separate.

## 8. EV and signal policies

The audit EV is:

`P(TARGET)*1.5R + P(PROTECTIVE)*(-1R) + P(TIME)*E[TIME_R|x] - cost_R`

Probabilities must be calibrated on validation data only.

Frozen validation-only coverage policies per direction:

- Conservative: top 0.25% by calibrated Strong-cost EV and EV > 0.
- Standard: top 0.50% and EV > 0.
- High coverage: top 1.00% and EV > 0.

Test data cannot be used to retune these policies.

## 9. Walk-forward

Random splitting is forbidden.

The four expanding folds are fixed in the JSON contract and cover tests from 2024-H2 through the end of the frozen 2026 snapshot. Each boundary uses a six-hour purge and six-hour embargo.

These historical tests are development diagnosis, not a pristine untouched holdout, because the historical period has been examined before. Formal evidence begins only after a frozen model package is committed.

## 10. Minimum gate before shadow evaluation

For each direction under the Standard policy:

- at least 100 resolved test trades,
- at least three of four test folds positive,
- aggregate Strong PF at least 1.20,
- aggregate Strong mean R at least +0.05,
- aggregate Strong maximum drawdown no more than 20R,
- removing the top five winners must leave nonnegative total R,
- no one fold may contribute more than 50% of positive R,
- Brier skill must be positive,
- Extreme-cost review must not destroy the Strong-EV thesis.

Failure means research-only. It does not permit shadow signalling.

## 11. Stage order

1. ML-00 design contract — complete.
2. ML-01 raw-data and timestamp audit.
3. ML-02 common causal feature engine.
4. ML-03 exact-M1 label engine.
5. ML-04 deterministic and linear baselines.
6. ML-05 tabular gradient-boosting models.
7. ML-06 calibration and Strong-cost EV policies.
8. ML-07 optional sequence-model comparison.
9. ML-08 frozen audit-only shadow package.
10. ML-09 prospective evaluation.

## 12. Controls

- audit-only remains ON,
- training code is not yet implemented,
- no model exists yet,
- no portfolio use,
- no live signal,
- no MT5 order,
- no Discord,
- no automatic retraining.

Next stage:

`ML-01_RAW_DATA_AND_TIMESTAMP_AUDIT`
