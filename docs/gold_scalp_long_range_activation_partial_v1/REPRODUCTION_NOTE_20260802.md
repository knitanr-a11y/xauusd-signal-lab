# Reproduction Note — GOLD SCALP LONG / RANGE ACTIVATION + PARTIAL EXIT V1

## Source candles

- `gold_v3_2023_2026_m1(3).csv`
- `goldsharp_m1(3).csv`
- the pre-existing structural setup ledger from the regime-specialist study

Duplicate M1 timestamps are resolved in the same source-priority order used by the preceding candle-only studies.

## Local scripts in the result package

- `gold_scalp_long_range_activation_partial_v1.py`
- `gold_scalp_range_failure_activation_partial_v1.py`
- `gold_scalp_retained_leads_descriptive_stack_v1.py`

## Pseudo-forward blocks

- 2023H1
- 2023H2
- 2024H1
- 2024H2
- 2025H1
- 2025H2
- 2026H1
- 2026JUL

For each target block:

1. older rows freeze the staged exit;
2. the immediately preceding half-year determines component eligibility;
3. the next block is evaluated without target threshold changes;
4. simultaneous and holding-overlap trades are removed globally.

## Main preregistration

### Trend LONG

- events: `HTF_PULLBACK_RESUME`, `COMPRESSION_RELEASE`, `EFFORT_RESULT_CONT`;
- structural and trade side: LONG;
- regimes: `TREND_ALIGNED_NORMAL`, `TREND_ALIGNED_HIGH`;
- activation: +3 USD within 15 minutes before -1 USD;
- retest: 0.5 or 1.0 USD;
- entry modes: frozen-level reclaim or favorable-extreme resume.

### Range follow

- events: `RANGE_SWEEP_RECLAIM`, `ROUND5_REJECTION`, `EMA_SNAPBACK`, `RUN_EXHAUSTION_FADE`;
- regimes: `RANGE_LOW`, `RANGE_ACTIVE`, `TRANSITION`;
- activation: +2 USD within 15 minutes before -1 USD;
- retest: 0.5 or 1.0 USD.

### Range failure

The same range setup list was tested with:

- pre-activation adverse failure fade;
- post-activation collapse fade.

Both range interpretations failed.

## Staged exits

- `P50_TP5_TP10_SL5_H240`
- `P67_TP5_TP10_SL5_H240`
- `P50_TP5_TP7P5_SL4_H180`

The exact-M1 resolver uses spread 0.30 USD once and protective-stop-first handling.

## Descriptive stack boundary

The four-lead stack combines two new Trend LONG rows and two previously observed VOLUME_ABSORPTION SHORT rows. It was assembled after component results were visible. It must never be described as untouched validation or deployment evidence.

## Package

The downloadable package created with this audit is:

`GOLD_SCALP_LONG_RANGE_ACTIVATION_PARTIAL_V1_RESULT_20260802.zip`

SHA256:

`e019c9ad792a55392909f6b096b4ca2299323c27dbc0cf2e8b268ac7cfbeb52f`
