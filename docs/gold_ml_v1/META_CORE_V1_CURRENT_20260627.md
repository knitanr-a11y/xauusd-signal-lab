# GML1 Meta Core v1 — Current Structure

`GML1-META-CORE v1` is the fixed machine-learning evaluation layer.

Input unit:

- one resolved raw event row;
- event ID and direction;
- 161 causal market features;
- Strong-cost R as the training target.

Model structure:

- XGBoost regression;
- separate LONG and SHORT estimators;
- event ID one-hot inputs;
- FULL and NO_TIME feature sets compared on validation data only;
- nonnegative affine calibration from validation data only;
- four fixed expanding walk-forward folds;
- six-hour purge and embargo;
- no test-period parameter selection.

Policy structure:

- conservative, standard and high-coverage validation thresholds;
- highest score wins when multiple events share a decision;
- one-position handling is applied only after raw and deduplicated reports are preserved.

Safety boundary:

- research fold models are reproducibility artifacts;
- no final promoted model exists;
- no live output path is enabled;
- a later version must pass the fixed gate and receive a separate manual decision.

The current event input layer is `GML1-EVENT-CORE v1`. Earlier candidate systems are not part of the current architecture.
