# GOLD V3 Stage299 — Stage280 wick and weight diagnostic

Stage298 identified the closest frame as:

- direction normalization: ON
- wick-column swap: OFF
- H4/D1 relative alignment: ON
- volume/spread features: ON
- engineered features: ON
- global onset: ON

The remaining mismatch was concentrated in the fixture score. Stage299 therefore compares the missing wick interpretation and class-weighting alternatives without promoting any model.

## Compared wick frames

1. raw upper/lower wick columns and raw reject-wick
2. raw upper/lower wick columns with reject-wick multiplied by predicted REV direction
3. directional reject-wick with raw wick columns removed
4. full upper/lower wick swap
5. directional reject-wick with raw H4/D1 alignment
6. directional reject-wick without volume/spread features

## Compared weighting

- scale_pos_weight
- class_weight=balanced
- no weighting
- scale_pos_weight with active bagging (`subsample_freq=1`)

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

The test sample uses the first 1606 future-valid non-neutral H4 rows from 2026, removing the four-row mismatch in Stage298.

## Safety

This diagnostic writes only:

`stage299_stage280_wick_weight_diagnostic.json`

It does not write model files, change thresholds, enable final signals, enable MT5 orders, or change Discord state.
