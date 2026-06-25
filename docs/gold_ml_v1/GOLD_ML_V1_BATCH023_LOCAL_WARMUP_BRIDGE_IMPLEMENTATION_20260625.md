# GOLD_ML_V1 Batch023 Local Warmup Bridge

Date: 2026-06-25  
Status: **AUDIT ONLY**

## Purpose

This implementation reconstructs every Batch023 trade that is reproducible from the frozen `gold_v3_2023_2026` candle snapshot and labels every output row as one of:

- `RAW_RECONSTRUCTED`
- `WARMUP_BRIDGE_EXACT`

`WARMUP_BRIDGE_EXACT` means the January 2023 decision requires pre-2023 indicator state that is absent from the frozen raw snapshot. Those rows are historical audit rows only and must never emit a live signal.

## Files

- `scripts/gold_ml_v1/replay/batch023_warmup_bridge_reconstruction.py`
- `scripts/gold_ml_v1/replay/run_batch023_warmup_bridge_local.py`
- `scripts/gold_ml_v1/replay/run_batch023_warmup_bridge.bat`
- `scripts/gold_ml_v1/replay/requirements-batch023-warmup-bridge.txt`

## Run on Windows

From the repository root:

```bat
scripts\gold_ml_v1\replay\run_batch023_warmup_bridge.bat "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\gold_v3_2023_2026" "C:\Users\regen\Downloads\GOLD_ML_V1_BATCH023_NINE_CANDIDATE_LOCAL_REPLAY_20260625.zip"
```

The second argument can be omitted when the verified ZIP is in Downloads or Desktop.

## What the runner does

1. Creates or reuses the isolated `.venv_batch023_bridge` environment.
2. Installs the frozen NumPy and pandas versions.
3. Verifies the SHA256 of all six raw CSV files.
4. Verifies the SHA256 and required registry members of the Batch023 ZIP.
5. Extracts only the expected registries to a short temporary path.
6. Moves a previous non-empty output directory to a timestamped backup.
7. Reconstructs the nine candidate registries.
8. Writes core and exact-schema bridge registries.
9. Exits with code 0 only when all nine candidates pass.

## Output

```text
outputs\gold_ml_v1\batch023_warmup_bridge_local
```

Key files:

- `LATEST_RUN_SUMMARY.txt`
- `local_run_metadata.json`
- `warmup_bridge_parity_report.csv`
- `warmup_bridge_rows.csv`
- `warmup_bridge_summary.json`
- 9 `*_warmup_bridge_core_registry.csv`
- 9 `*_warmup_bridge_exact_schema_registry.csv`

## PASS criteria

For all nine candidates:

- missing/extra = 0
- entry mismatch = 0
- exit mismatch = 0
- R mismatch = 0
- direction mismatch = 0

## Verified result

The local launcher was executed against the audited raw snapshot and verified Batch023 ZIP. All nine candidates passed with exit code 0.

This is a separately versioned warmup bridge, not raw-only parity. Full raw-only parity still requires pre-2023 history or serialized indicator state.
