# Next Chat Handoff — Meta Core Locked / MLR2 v1 Failed / v2 Research-Only

Repository: `knitanr-a11y/xauusd-signal-lab`

## Read first

1. `docs/gold_ml_v1/GML1_META_MODEL_CORE_V1_LOCK_20260627.md`
2. `config/gold_ml_v1/mlr1_meta_model_core_contract_v1_20260627.json`
3. `config/gold_ml_v1/mlr1_stage_status_addendum_meta_core_locked_20260627.json`
4. `config/gold_ml_v1/mlr2_candidate_contract_v1_20260627.json`
5. `config/gold_ml_v1/mlr2_v1_result_audit_20260627.json`
6. `config/gold_ml_v1/mlr2_candidate_contract_v2_research_20260627.json`
7. `config/gold_ml_v1/mlr2_v2_research_result_audit_20260627.json`

## Machine-learning core is fixed

`GML1-META-CORE v1` is now the common candidate evaluation layer:

- XGBoost direct Strong-R regression;
- separate LONG and SHORT estimators;
- 161 causal features plus candidate-ID one-hot;
- no classifier in the decision path;
- FULL versus NO_TIME selected by validation MSE only;
- validation-only nonnegative affine calibration;
- four fixed walk-forward folds with 6-hour purge and embargo;
- validation-only coverage thresholds;
- raw, dedup and one-position reporting;
- fixed numeric gates;
- deployment blocked unless a later manual promotion explicitly changes status.

The complete research runner, pinned dependencies, tests and Windows replay files are on main. Do not change this core during candidate redesign. A core change requires a new explicit core version.

## Local implementation boundary

Local research replay is implemented. Live model inference is intentionally not implemented.

- research fold models may be written for reproducibility;
- `DEPLOYMENT_BLOCKED.json` must remain present;
- do not connect research models to live, shadow, final signal, Discord or MT5;
- do not ask the user to run local experiments before assistant-side validation.

## MLR2 v1

MLR2 v1 was frozen label-free before outcomes were read:

- ten environment/setup/confirmation candidates;
- proposal SHA `0afe40cf2d856d7fbb195c163efb801ca7f964da9daad6097d14d774af119cfe`;
- 3,156 raw proposals;
- no LONG/SHORT same-time conflict.

After label join and unchanged Meta Core evaluation, conservative one-position was:

- 238 trades;
- LONG 238, SHORT 0;
- Strong `-24.6724R`, PF `0.8375`;
- Extreme `-35.0095R`;
- not promoted.

MLR2 v1 is immutable and must remain recorded as a failed candidate version.

## MLR2 v2 research

MLR2 v2 is explicitly performance-informed. It contains four candidates:

- H1 trend pullback LONG from MLR2 v1;
- compression breakout SHORT from MLR2 v1;
- strict high-vol exhaustion reversal LONG;
- strict high-vol exhaustion reversal SHORT.

Label-free frozen reference:

- 831 proposals;
- LONG 495, SHORT 336;
- no overlap or direction conflict;
- proposal SHA `3212f70556a38f6d35d6000c18a6750aa620596d3ff9b54c7d7c21d358604eca`.

Historical unchanged Meta Core standard policy:

- 319 trades;
- LONG 213, SHORT 106;
- Strong `+36.9783R`, PF about `1.211`;
- Extreme `+17.3080R`;
- drawdown `12.0472R`;
- all frozen numeric gates passed.

Manual promotion is still rejected because:

- v2 was assembled after historical candidate performance was reviewed;
- F1 generated zero selected trades;
- F4 had only `+2.0267R` Strong and `-1.7480R` Extreme;
- several later calibration slopes were zero, meaning broad candidate acceptance rather than event ranking;
- H1 pullback LONG was negative under Extreme cost;
- the untouched post-boundary snapshot had only four events and total Strong `-1.6873R`.

Do not call v2 a validated or usable model. Do not modify v2 conditions after this result.

## Current next step

Stop iterative threshold tuning on the inspected historical snapshot. The legitimate next development task is one of these, without loosening controls:

1. retain v2 as a fixed research challenger and collect later resolved events; or
2. design a new candidate version from market structure before reading its outcomes, with a separately declared evaluation boundary.

No model is promoted. Audit-only, shadow, live, final signal, MT5 order and Discord remain OFF.
