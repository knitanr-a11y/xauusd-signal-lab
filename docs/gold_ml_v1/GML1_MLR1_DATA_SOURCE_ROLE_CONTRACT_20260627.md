# GML1-MLR1 — historical and live data-source roles

Date: 2026-06-27  
Status: `DATA_SOURCE_ROLES_FROZEN_AUDIT_ONLY`

Machine-readable authority:

`config/gold_ml_v1/mlr1_data_source_role_contract_20260627.json`

## Historical development data

Use only this folder for the existing 2023–2026 research snapshot:

```text
C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\gold_v3_2023_2026
```

Expected family:

```text
gold_v3_2023_2026_*.csv
```

This source is for:

- source audit,
- pinned feature and label replay,
- historical walk-forward development,
- model research and backtesting.

It must not be used as the live inference source.

The current ML-02 and ML-03 Windows runners must receive this exact directory as their `raw-dir` argument.

## Live operational data

The future live/shadow source is the MT5 `Files` root:

```text
C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files
```

Live file family:

```text
goldsharp_*.csv
```

Only `goldsharp_*.csv` located directly in the `Files` root is treated as live input. The `gold_v3_2023_2026` subdirectory is explicitly excluded from live discovery.

The live files must not be used for MLR1-v1 training, feature selection, calibration or policy-threshold selection. After a future frozen model package exists, they are reserved for audit-only shadow and prospective evaluation.

## No fallback or mixing

The following are forbidden:

- recursively searching the `Files` root and accidentally loading the historical subdirectory,
- replacing historical files with `goldsharp_*.csv` during development,
- replacing live files with the historical snapshot at runtime,
- concatenating historical and live source families silently,
- falling back from one source role to another when a file is missing.

Every output manifest must identify the source role, resolved paths, hashes, row counts and time range.

## Shared candle semantics

Both sources use the same semantic rules:

- CSV `time` is MT5 server bar-open time,
- latest CSV row is closed by contract,
- only closed higher-timeframe bars may be joined,
- exact M1 is mandatory where required,
- the same causal feature definitions must be used.

The source adapters are different, but feature meaning must remain identical.

## Current state

The historical hash-locked adapter is implemented in ML-02/ML-03.

The `goldsharp_*.csv` live adapter is not implemented yet. It will be designed separately before ML-08 shadow evaluation and will remain audit-only until later activation gates pass.

Live signal, final signal, MT5 order and Discord remain OFF.
