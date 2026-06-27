# GML1-MLR1 Stage ML-04 — result audit

Date: 2026-06-27  
Status: `FULL_WINDOWS_REPLAY_AUDITED_NO_MODEL_PROMOTED_ML05_JUSTIFIED`

Machine-readable authority:

`config/gold_ml_v1/mlr1_stage_ml04_result_audit_20260627.json`

## Artifact verification

The uploaded Windows outputs match the hashes printed by the ML-04 summary:

- fold metrics: `8a243d481d6a58761c360c73015a00edbe0bdd67b93217fde70352c36c398693`
- policy metrics: `926b8a8e46a97356a56ab5f32878b0c0365bae9efba965c8c737c364da34e1e4`
- test predictions: `d15e899854c6d0a524cf10eaa2f3d47ecf2a23640dc096d60228d91afe820ec0`
- coefficients: `409b1f5f0b6994e7179c4fd6f7b25dfd2d74d339c1983b00ecab6fdc9b2ddf5d`

Feature/label join parity is complete: 148,317 labels joined to 148,317 rows.

## Unconditional execution

Always entering while flat is negative in all four test folds.

| Direction | Trades | Strong total R | Strong mean R | Strong PF |
|---|---:|---:|---:|---:|
| LONG | 10,603 | -1,026.47 | -0.0968 | 0.850 |
| SHORT | 10,780 | -1,664.70 | -0.1544 | 0.770 |

The label geometry does not contain a free unconditional edge. Positive selected results therefore require ranking or selection.

## LONG

No ML-04 LONG lane is retained.

The best-looking aggregate is logistic Conservative, but:

- Strong PF is only 1.047,
- Extreme total is negative,
- removing the fold-level top five winners makes total R negative.

Standard is essentially flat and High coverage is negative. Ridge also fails cost and concentration review.

Decision:

`REJECT_ALL_ML04_LINEAR_LONG_MODELS`

LONG remains in ML-05 as a required negative-control lane, not because ML-04 found a usable LONG model.

## SHORT multinomial logistic

The SHORT classifier contains meaningful ranking evidence.

| Policy | Trades | Positive folds | Strong total R | Strong mean R | Strong PF | Extreme total R | Extreme PF | Top-5 removed R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Conservative | 185 | 2/4 | +22.64 | +0.1224 | 1.222 | +16.03 | 1.152 | +0.42 |
| Standard | 335 | 2/4 | +41.31 | +0.1233 | 1.223 | +28.74 | 1.150 | +19.06 |
| High coverage | 567 | 3/4 | +57.80 | +0.1019 | 1.182 | +33.56 | 1.101 | +28.60 |

This is not a one-winner illusion: Standard and High coverage remain positive after removing the top five winners from every fold.

However, the fold distribution is not stable.

Standard Strong R:

- F1: 0 trades / 0R,
- F2: -5.85R,
- F3: +15.82R,
- F4: +31.34R.

High-coverage Strong R:

- F1: +6.35R,
- F2: -8.59R,
- F3: +16.39R,
- F4: +43.65R.

F4 contributes more than 65% of positive-fold R in Standard and High coverage. Conservative is even more concentrated. The classifier is detecting a useful later-regime SHORT pattern, but it has not demonstrated environment-independent stability.

Decision:

`RESEARCH_SIGNAL_PRESENT_BUT_NOT_SHADOW_READY`

## Probability and regression quality

The logistic model improves test log loss over the unconditional class-rate baseline in 5 of 8 fold/direction comparisons.

But multiclass Brier skill is negative in all 8 comparisons. The raw probabilities are not calibrated and must not be treated as TP/SL probabilities or direct EV.

Ridge test MSE is worse than the unconditional mean-R baseline in all 8 fold/direction comparisons. Ridge is rejected.

## Coefficient stability

SHORT TARGET standardized coefficient correlations across folds are approximately 0.61 to 0.89. Recurring groups include:

- MT5 server-hour cyclic features,
- H4 EMA50-to-EMA100 gap divided by ATR,
- D1 EMA slope,
- volatility/spread state,
- tick-volume ratios,
- distance from completed multi-day highs.

The repeated signs suggest structure rather than completely random coefficients. However, server-hour features are among the largest coefficients. ML-05 therefore requires a frozen no-server-hour ablation so a narrow session proxy cannot be mistaken for general regime learning.

## Frozen shadow-gate result

No ML-04 policy passes the previously frozen shadow gate.

- LONG: fail.
- SHORT Conservative: fail on positive-fold count, Brier skill and fold concentration.
- SHORT Standard: fail on positive-fold count, Brier skill and fold concentration.
- SHORT High coverage: fail on Strong PF, maximum fold DD, Brier skill and fold concentration.

No model is promoted or shadow-enabled.

## Decision for ML-05

Proceed to histogram gradient boosting under the same:

- 161 frozen features,
- four folds,
- purge/embargo,
- policy coverages,
- one-open rule,
- Strong and Extreme costs.

Evaluate both directions. LONG is the negative-control lane; SHORT is the primary research lane.

ML-05 must also run a no-server-hour feature ablation. Hyperparameters remain validation-only. Test outcomes cannot change the feature definitions, coverage levels or fold boundaries.

Probability calibration remains deferred to ML-06.

## Controls

- audit-only,
- no model promoted,
- no shadow activation,
- no candidate-stack change,
- no portfolio use,
- no live adapter,
- no final signal,
- no MT5 order,
- no Discord.
