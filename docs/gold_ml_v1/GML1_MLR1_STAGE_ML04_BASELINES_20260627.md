# GML1-MLR1 Stage ML-04 — deterministic and linear baselines

Date: 2026-06-27  
Status: `IMPLEMENTED_SYNTHETIC_VALIDATED_FULL_WINDOWS_REPLAY_PENDING`

## GitHub implementation

- Engine: `scripts/gold_ml_v1/mlr1/run_ml04_baselines.py`
- Frozen contract: `config/gold_ml_v1/mlr1_ml04_contract_v1_20260627.json`
- Unit tests: `tests/gold_ml_v1/test_mlr1_ml04_baselines.py`
- Dependencies: `scripts/gold_ml_v1/mlr1/requirements-ml04.txt`
- Windows runner: `scripts/gold_ml_v1/mlr1/run_ml04_baselines.bat`
- Validation record: `config/gold_ml_v1/mlr1_stage_ml04_baseline_validation_20260627.json`

## Purpose

ML-04 determines whether simple, auditable models contain any usable out-of-sample information before gradient boosting or sequence models are allowed.

No ML-04 model is promoted, calibrated or used live.

## Inputs

ML-04 reads the already accepted registries only:

- ML-02 feature registry SHA256: `81a3c33c61d07eebbb13514965539a05d5f150e2ce521e613e2089be01d94a2b`
- ML-03 label registry SHA256: `c897a00905ca3edc47eff29a159beff21e1c1aafc66c6c41558ba3dfd2a0d7ed`
- model features: 161

The engine refuses a hash mismatch.

## Baselines

Five baselines are evaluated independently for LONG and SHORT:

1. Training-only unconditional outcome class rates.
2. Training-only unconditional mean Strong R.
3. Always-trade while flat under one-open execution.
4. Standardized multinomial logistic outcome model.
5. Standardized Ridge regression on Strong R.

The logistic model converts raw class probabilities to an uncalibrated Strong-R score using class-conditional Strong-R means calculated from the training segment only.

## Walk-forward

Four expanding folds are fixed from 2024-H2 through the end of the frozen snapshot.

Every train/validation and validation/test boundary uses:

- six-hour purge before the boundary,
- six-hour embargo after the boundary.

The first three test periods also remove their final six hours so their outcomes do not spill into the following calendar segment. The final 2026 test uses the exact resolved snapshot tail.

Random splitting is forbidden.

## Validation-only selection

Logistic C grid:

`0.01, 0.1, 1.0`

Selection metric:

minimum validation multiclass log loss.

Ridge alpha grid:

`1, 10, 100, 1000`

Selection metric:

minimum validation mean squared error.

Ties use the smaller regularization parameter.

The selected model is not refitted on validation data. This preserves direct transfer of the validation score thresholds to test.

## Policies

For each fold, direction and model, validation data alone sets the score threshold:

- Conservative: top 0.25%.
- Standard: top 0.50%.
- High coverage: top 1.00%.

The quantile method is `higher`. A test decision must also have score greater than zero. Test thresholds are never changed after outcomes are inspected.

## One-open execution

Selected test decisions are ordered by decision time.

- one open position per direction,
- a decision earlier than the prior accepted trade exit is skipped,
- a decision exactly equal to the prior exit time is allowed,
- LONG and SHORT are not netted against each other in ML-04.

Cross-direction and portfolio rules are deferred to a later stage.

## Metrics

ML metrics:

- multiclass log loss,
- multiclass Brier score,
- Strong-R MSE and MAE.

Trading diagnostics under Strong and Extreme costs:

- raw signals and accepted one-open trades,
- positive rate,
- mean and total R,
- profit factor,
- maximum drawdown,
- maximum losing streak,
- top-five and top-five-percent winner removal,
- positive test-fold count.

No aggregate PF is sufficient by itself.

## Local validation

Seven synthetic tests passed:

1. One-open overlap handling and equality rule.
2. Purge and embargo boundaries.
3. Validation quantile method.
4. R and profit-factor calculations.
5. Multiclass Brier calculation.
6. Deterministic gzip output.
7. Logistic and Ridge validation-only selection.

## Windows execution

From the repository root, install the pinned dependencies once:

```bat
py -3.12 -m pip install -r scripts\gold_ml_v1\mlr1\requirements-ml04.txt
```

Then run:

```bat
scripts\gold_ml_v1\mlr1\run_ml04_baselines.bat
```

Expected output directory:

`outputs\gold_ml_v1\mlr1\ml04_baselines_v1`

Expected files:

- `mlr1_ml04_fold_metrics.csv`
- `mlr1_ml04_policy_metrics.csv`
- `mlr1_ml04_test_predictions.csv.gz`
- `mlr1_ml04_coefficients.csv.gz`
- `mlr1_ml04_summary.json`

## Interpretation rule

The result must be reviewed by fold and direction.

A linear model is not considered useful merely because one policy has positive aggregate R. At minimum, compare it with both no-skill baselines and the executable always-trade baseline, inspect test-fold consistency, Extreme-cost survival and winner concentration.

## Controls

- audit-only remains ON,
- no model is promoted,
- no probability calibration has occurred,
- no candidate stack modification,
- no portfolio use,
- no live adapter,
- no final signal,
- no MT5 order,
- no Discord.
