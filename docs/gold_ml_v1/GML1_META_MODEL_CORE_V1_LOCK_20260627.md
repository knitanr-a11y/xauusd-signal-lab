# GML1 Meta-Model Core v1 — Structure Lock

Date: 2026-06-27  
Status: `RESEARCH_META_MODEL_STRUCTURE_FROZEN_NOT_DEPLOYABLE`

## 1. What is frozen

The machine-learning layer is independent from candidate design. A candidate redesign may change proposal definitions and candidate IDs only in a separately versioned candidate contract. It must not silently change this ML core.

The frozen ML core consumes one raw candidate event per row before decision deduplication or one-position handling.

- Target: `strong_r` after Strong-cost assumptions.
- Estimator: XGBoost histogram `XGBRegressor`.
- LONG and SHORT are trained separately.
- Inputs: 161 causal market features plus candidate-ID one-hot columns.
- Classifier output is not used in the decision path.
- FULL and NO_TIME feature sets are compared using validation Strong-R MSE only.
- The selected raw score receives validation-only affine calibration.
- Calibration slope is constrained to `[0, 2]`.
- Test data never selects feature sets, calibration or thresholds.

The prior outcome classifier is removed from the decision path because validation selected classifier weight `0.0` in all eight fold-direction fits. Outcome and probability diagnostics may be studied separately, but they must not affect candidate acceptance in Core v1.

## 2. Causality and walk-forward

Four fixed folds are used. Each fold has expanding training history, a validation segment and a later test segment.

- Purge: 6 hours.
- Embargo: 6 hours.
- A historical event is available only after `exit_time` exists.
- Train and validation rows require `exit_time <= applicable segment cutoff`.
- Label, exit, fill, R and collision columns are forbidden model inputs.
- Candidate proposals must already be frozen before labels or candidate performance are read.

## 3. Policy layer

Validation-only coverage targets are fixed separately by direction:

- conservative: 0.25% of eligible M15 decisions;
- standard: 0.50%;
- high coverage: 1.00%.

A score must be positive and meet the validation threshold. At one decision time, the candidate with the highest calibrated predicted Strong R wins; exact ties use candidate ID ascending. One-position accepts a later decision only when `decision_time >= active exit_time`.

Raw, decision-deduplicated and one-position results must all be reported.

## 4. Promotion gates

A research result is not deployable unless all frozen gates pass:

- at least 100 total OOS trades;
- at least 100 OOS trades for LONG and 100 for SHORT;
- at least three positive test folds;
- Strong PF at least 1.20;
- Strong mean R at least 0.05;
- Strong maximum drawdown no more than 20R;
- result remains nonnegative after removing the five largest winners;
- no single positive fold contributes more than 50% of positive-fold R;
- Extreme-cost total R is positive.

Passing the numeric gate still requires manual audit. It never activates live execution automatically.

## 5. Reference replay

The locked runner exactly reproduces the prior ML-06 conservative one-position audit:

- trades: 113;
- LONG: 83;
- SHORT: 30;
- Strong total: +11.6373977593109R;
- Strong PF: 1.1848033711294401;
- Extreme total: +6.169841678618901R;
- Strong maximum drawdown: 6.25765586492R;
- fold R: F1 `+0.03615627483`, F2 `-0.76471919747`, F3 `+10.64851667979`, F4 `+1.717444002159`.

This reference fails the frozen promotion gates for direction sample count, Strong PF and fold concentration. It remains research-only.

Two complete runs produced identical SHA256 values for predictions, metrics, diagnostics, summary, deployment block and all eight fold-model artifacts.

## 6. Local research implementation

Files:

- `scripts/gold_ml_v1/mlr1/run_mlr1_meta_model_research.py`
- `scripts/gold_ml_v1/mlr1/verify_mlr1_meta_core_reference.py`
- `scripts/gold_ml_v1/mlr1/run_mlr1_meta_model_research.bat`
- `scripts/gold_ml_v1/mlr1/check_mlr1_meta_model_research_deps.bat`
- `scripts/gold_ml_v1/mlr1/requirements_mlr1_meta_core_v1.txt`
- `config/gold_ml_v1/mlr1_meta_model_core_contract_v1_20260627.json`
- `tests/gold_ml_v1/test_mlr1_meta_model_core.py`

The Windows runner writes to `outputs/gml1/meta_core_research_v1`. It saves fold research models for reproducibility, but also writes `DEPLOYMENT_BLOCKED.json`. There is no final model, live inference, shadow signal, Discord output or MT5 order path.

## 7. What candidate redesign may change

Candidate redesign may change:

- named structural candidate families;
- candidate IDs under a new version;
- label-free proposal states and state transitions;
- the number and density of candidate events.

Candidate redesign may not change:

- ML target, estimator or fixed parameters;
- fold boundaries, purge or embargo;
- validation-only calibration and thresholds;
- cost definitions;
- promotion gates;
- live or order controls.

Any ML-core change requires a new explicit core version and must not overwrite Core v1.
