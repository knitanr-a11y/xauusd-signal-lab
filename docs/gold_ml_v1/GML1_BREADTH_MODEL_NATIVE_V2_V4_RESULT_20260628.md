# GML1 Breadth and Model-Native Candidate Search V2–V4 Result

Date: 2026-06-28  
Mode: audit-only

## Objective

Increase useful trade-candidate density without accepting low-quality PF 1.1–1.3 candidates. The frozen minimum individual gate was Strong PF 1.5 in both 2024 and 2025, combined PF 1.7, positive Strong R in both years, Extreme PF 1.1 in both years, and adequate trade count.

## V2 — Breadth-first structural M5 candidates

- 18 original symmetric M5 families and 8 separately identified density variants.
- 52 directional candidates.
- 53,645 raw proposals saved before labels, deduplication or one-position handling.
- 33 candidates passed the label-free density requirement.
- 53,501 proposals received resolved exact-M1 labels.
- 38,682 rows remained after candidate-level one-position handling.
- No candidate passed the strict 2024 and 2025 admission gate.
- The best observed structural candidate still had 2024 Strong PF 0.958 and 2025 Strong PF 1.251, so it was not eligible for ML rescue.

## V3 — Every-M5 model-native tabular candidates

- 243,036 causal M5 feature rows.
- 484,218 resolved LONG/SHORT exact-M1 labels.
- Eight mutually exclusive direction-regime sleeves.
- Direction-wide LightGBM, XGBoost and linear models with purged 2023 OOF calibration produced no 2024 sleeve passing the individual gate.
- Score decomposition into probability-only, Strong-only, Extreme-only and pairwise consensus also produced no passing sleeve.

### V3C specialist models

Separate LightGBM, XGBoost, CatBoost and linear models were trained per direction-regime sleeve with 30-minute overlap weighting.

One 2024 individual sleeve passed:

- `GML1-MN3-LOW_VOL-L`
- CatBoost specialist
- probability/Strong minimum score
- two-percent retention
- 66 one-position trades
- Strong positive rate 56.06%
- Strong PF 1.735
- Extreme PF 1.368

Unchanged 2025 confirmation failed:

- 23 trades
- Strong positive rate 34.78%
- Strong PF 0.707
- Strong R -4.75
- Extreme PF 0.634

It was rejected without a 2026 rescue.

## V4 — Raw M5 path specialists

The previous 32 completed M5 bars were preserved as a 160-minute ordered path with ten direction-normalized channels per bar, then combined with the closed M15/H1/H4/D1 context.

- 215,531 valid continuous-sequence rows.
- Sequences crossing a weekend, missing bar or data gap were excluded.
- LightGBM, CatBoost and linear models were trained separately per sleeve.

One 2024 individual sleeve passed:

- `GML1-MN4-LOW_VOL-L`
- linear raw-path model
- probability/Strong/Extreme mean minus one standard deviation
- one-percent retention
- 63 one-position trades
- Strong positive rate 58.73%
- Strong PF 1.866
- Extreme PF 1.526

Unchanged 2025 confirmation failed:

- only one row remained above the frozen one-percent reference gate
- the row lost -1.04 Strong R
- Strong PF 0.0
- Extreme PF 0.0

It was rejected without evaluating 2026.

## Conclusion

Candidate count was successfully increased, but no candidate was both sufficiently profitable and stable in unchanged 2025 confirmation. The failure is not caused by refusing to use machine learning: structural rules, every-M5 models, sleeve specialists, purged OOF calibration, raw-path features, LightGBM, XGBoost, CatBoost and linear models were all evaluated.

The current OHLCV/spread representation does not provide a stable enough ranking edge for the fixed six-hour TP1.5/SL1.0 label.

## Next valid hypothesis

Do not continue threshold tuning on V2–V4. The next separately versioned stage should add causal M1 microstructure information available before the M5 decision:

- spread median, upper percentile and expansion rate;
- tick-volume burst and concentration;
- one-, five-, fifteen-, thirty- and sixty-minute realized volatility;
- directional efficiency and path entropy;
- M1 close-location and wick aggregation;
- sub-bar sweep/reclaim counts;
- acceleration and stagnation measures.

Candidate and model selection must remain 2023 training, 2024 selection, unchanged 2025 confirmation and 2026 diagnostic only. No live, final-signal, Discord or MT5 control is enabled.
