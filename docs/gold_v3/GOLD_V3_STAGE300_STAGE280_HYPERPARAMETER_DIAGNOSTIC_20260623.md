# GOLD V3 Stage300 — Stage280 hyperparameter parity diagnostic

Stage299 fixed the remaining feature candidates to three frames:

1. normalized direction + no wick-column swap + directional reject-wick
2. normalized direction + no wick-column swap + raw reject-wick
3. normalized direction + directional reject-wick + raw wick columns removed

Stage300 searches only model-training settings. It does not promote any result.

## Search sequence

1. positive-class weight grid for all three frames;
2. coordinate search around the best weight for:
   - n_estimators
   - learning_rate
   - num_leaves
   - max_depth
   - min_child_samples
   - reg_alpha / reg_lambda
   - colsample_bytree
   - random_state
   - max_bin
   - min_split_gain
   - min_child_weight
3. local refinement around the three best candidates for weight, tree count, and learning rate.

## Exact comparison targets

- fit_n = 4974
- cal_n = 1809
- test_n = 1606
- fit positives = 245
- test positives = 65
- q95 threshold = 0.5927349103795366
- fixture score = 0.5949591748604749
- test ROC-AUC = 0.6904307891978236
- test PR-AUC = 0.08009367826075599
- q90 selected/hits = 120/10
- q95 selected/hits = 64/8
- q97.5 selected/hits = 25/3
- q99 selected/hits = 11/1

## Output

`stage300_stage280_hyperparameter_diagnostic.json`

Only the top-ranked configurations and any exact match are written. No model file, threshold, live signal, MT5 order, or Discord state is changed.
