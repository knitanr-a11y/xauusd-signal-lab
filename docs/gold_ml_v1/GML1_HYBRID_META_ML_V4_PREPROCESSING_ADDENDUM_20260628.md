# GML1 Hybrid Meta-ML V4 Shared Preprocessing Addendum

Date: 2026-06-28
Mode: audit-only

This implementation rule is frozen before completed V4 results are produced.

For each annual model version and each component-model family:

- fit one preprocessing transformer on the complete resolved training registry available at that cutoff;
- numeric features use the preprocessing defined by the component model;
- categorical features use one-hot encoding with unknown-value handling;
- transform the full training and target registries once;
- global, direction-specific and candidate-specific estimators use subsets of the same transformed matrix;
- no validation-year or future-year row is used to fit the transformer;
- specialist sample selection, shrinkage weights, model parameters and score behavior remain unchanged.

This changes computation only. It avoids repeatedly rebuilding identical transformations and does not alter the causal feature values or selection contract.
