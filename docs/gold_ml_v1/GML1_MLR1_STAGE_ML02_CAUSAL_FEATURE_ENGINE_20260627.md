# GML1-MLR1 Stage ML-02 — common causal feature engine

Date: 2026-06-27  
Status: `IMPLEMENTED_AND_CONTAINER_VALIDATED_USER_PC_PINNED_REPLAY_PENDING`

## GitHub implementation

- Engine: `scripts/gold_ml_v1/mlr1/build_features.py`
- Frozen contract: `config/gold_ml_v1/mlr1_feature_contract_v1_20260627.json`
- Unit tests: `tests/gold_ml_v1/test_mlr1_features.py`
- Dependencies: `scripts/gold_ml_v1/mlr1/requirements-mlr1.txt`
- Windows runner: `scripts/gold_ml_v1/mlr1/run_build_features.bat`
- Validation record: `config/gold_ml_v1/mlr1_stage_ml02_feature_validation_20260627.json`

## Purpose

The same feature engine is intended for historical development, later walk-forward evaluation and future audit-only shadow inference. Separate training and live feature implementations are forbidden.

The engine does not create labels and does not train a model.

## Input enforcement

Before feature construction, the engine checks the exact SHA256 of M1, M15, H1, H4 and D1 against the frozen contract. Any mismatch stops execution.

CSV `time` is parsed as MT5 server bar-open time. Duplicate or unsorted timestamps stop execution.

## Decision and join rules

- Every closed M15 bar creates a decision time at bar-open plus 15 minutes.
- An exact M1 bar-open at that decision time is mandatory.
- H1, H4 and D1 features are joined by bar-close time.
- Only a higher-timeframe bar with close time less than or equal to the M15 decision may be used.
- Missing exact M1, missing closed higher-timeframe history or incomplete feature warmup causes the row to be excluded.
- No next-M1 fallback, interpolation or warmup bridge is used.

## Feature structure

The contract freezes 161 model features across:

- M15,
- H1,
- H4,
- D1,
- completed-day and completed-five-day cross-timeframe distances,
- MT5 server hour and weekday cyclic encodings.

The feature families include:

- log returns,
- candle body, range and wick structure normalized by ATR,
- ATR ratios and lagged ATR percentile,
- EMA gaps and slopes normalized by ATR,
- RSI, ADX and normalized MACD,
- Bollinger width and location,
- tick-volume ratios and lagged percentile,
- spread divided by ATR and lagged spread percentile,
- distances from prior rolling highs and lows normalized by ATR.

Raw absolute entry price and ATR price distance are included only as metadata for the future label engine. They are not in the model feature list.

## Distribution causality

Lagged percentile features expose the percentile of the immediately preceding bar in a trailing window ending at that preceding bar. The current decision value is not used in its own distribution baseline.

Rolling prior-high and prior-low distances use `shift(1)` before the rolling extrema.

## Deterministic output

The feature registry is written as deterministic gzip CSV. The gzip filename field and modification time are fixed so identical content has an identical hash even when the output path changes.

Expected output directory:

`outputs/gold_ml_v1/mlr1/ml02_features_v1`

Files:

- `mlr1_features_v1.csv.gz`
- `mlr1_feature_columns_v1.json`
- `mlr1_feature_manifest_v1.json`

## Full-snapshot result

- M15 decisions: 81,781
- Missing exact M1: 899
- Missing closed higher timeframe: 91
- Feature warmup/nonfinite exclusion: 6,623
- Eligible rows: 74,168
- Model features: 161
- First eligible decision: 2023-04-18 01:15
- Last eligible decision: 2026-06-19 19:45

Expected hashes:

- feature registry: `81a3c33c61d07eebbb13514965539a05d5f150e2ce521e613e2089be01d94a2b`
- feature columns: `b6f588f1e091906be3f2b3c1623898d59c12b28017d7a4e1209b2ec915af4d60`

Two independent full runs produced the same feature-registry hash.

## Causality validation

The feature table passed these checks:

- every H1/H4/D1 source close is at or before its decision time,
- all model feature values in eligible rows are finite,
- all 161 model names are unique,
- no absolute price metadata appears in the model feature list,
- rebuilding from data truncated at 2024-12-31 12:00 produced the same 39,987 earlier rows as the full dataset,
- maximum numeric difference in that future-append comparison was exactly 0.

## Unit tests

Six tests passed in the container:

1. Wilder RMA uses an SMA seed.
2. Lagged percentile excludes the current value.
3. As-of joins cannot select a future higher-timeframe bar.
4. Future appended candles cannot change existing timeframe features.
5. Model columns exclude absolute-price metadata.
6. Gzip output is deterministic across filenames.

Run from the repository root:

```bat
py -3.12 -m unittest tests.gold_ml_v1.test_mlr1_features -v
```

## Windows full replay

```bat
scripts\gold_ml_v1\mlr1\run_build_features.bat "C:\path\to\raw"
```

The user-PC environment must confirm the expected row count and both expected output hashes before cross-environment exact parity is claimed.

Container validation used Python 3.13.5, NumPy 2.3.5 and pandas 2.2.3. The target runner pins Python 3.12, NumPy 2.2.6 and pandas 2.2.3, so the pinned user-PC replay remains an explicit acceptance step.

## Controls

- audit-only remains ON,
- no labels exist yet,
- no model has been trained,
- no candidate stack was modified,
- no portfolio or live use,
- no final signal,
- no MT5 order,
- no Discord.

Next stage after pinned feature replay:

`ML-03_EXACT_M1_LABEL_ENGINE`
