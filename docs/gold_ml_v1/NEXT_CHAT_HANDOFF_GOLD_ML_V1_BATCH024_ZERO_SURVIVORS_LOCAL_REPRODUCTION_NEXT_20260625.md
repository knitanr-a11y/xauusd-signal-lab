# GOLD_ML_V1 Batch024 — Zero Survivors, Local Reproduction Next

Date: 2026-06-25

Formal status:

`GOLD_ML_V1_027_BATCH024_ASSISTANT_RESULT_FROZEN_LOCAL_REPRODUCTION_READY_AUDIT_ONLY`

## Assistant-side exploration completed

The user supplied the frozen 2023-2026 raw CSV files. All six uploaded file hashes matched the previously recorded hashes. Batch024 used only M1, M15 and H1 as predeclared.

The CSV `time` column is bar-open time in MT5 server time:

- M1 close = `time + 1 minute`;
- M15 close = `time + 15 minutes`;
- H1 close = `time + 1 hour`.

M15 candidate decisions occur at M15 close. Entry requires an exact M1 bar whose open time equals that M15 close. Confirmed H1 context is joined by H1 close time with no future H1 bar.

## Result

- predeclared cells: 36;
- year metric rows: 144;
- signal/trade audit rows: 25,327;
- 2023 gate PASS: 4;
- 2024 gate PASS: 17;
- 2025 gate PASS: 15;
- all-year survivors: 0.

A zero-survivor result is valid. No rescue tuning, gate change, grid expansion or post-result filter was performed.

The four 2023-pass cells were:

- `GML1-EXP024-S-G000-R40-ER`: 2024 PASS, 2025 FAIL;
- `GML1-EXP024-S-G015-R40-ER`: 2024 PASS, 2025 FAIL;
- `GML1-EXP024-S-G030-R40-ER`: 2024 FAIL, 2025 FAIL;
- `GML1-EXP024-L-G030-R35-RC`: 2024 PASS, 2025 FAIL.

No Batch024 candidate was added to the frozen nine. No candidate was promoted or registered.

Frozen result record:

`config/gold_ml_v1/exploration_batch024_assistant_result_20260625.json`

The assistant replayed the complete exploration twice. Attempt registry, year metrics, full trade registry and survivor registry were equal across both replays.

## Canonical local reproduction

Local reproduction is now allowed only as a parity check against the assistant-frozen result.

User-facing launcher:

`RUN_GOLD_ML_V1_NEXT.bat`

Current phase BAT:

`scripts/gold_ml_v1/exploration/windows/reproduce_batch024.bat`

The local reproducer:

1. validates the exact frozen M1/M15/H1 hashes;
2. recalculates the same 36 predeclared cells;
3. writes canonical CSVs with fixed date, float, null and line-ending formats;
4. compares all four canonical SHA-256 values with the assistant result;
5. fails closed if any row count or output hash differs.

The local run does not select candidates, retune conditions, expand the grid or alter the frozen nine.

Output directory:

`outputs/gold_ml_v1/exploration_batch024_local_reproduction`

Upload file:

`outputs/gold_ml_v1/exploration_batch024_local_reproduction/UPLOAD_THIS_GOLD_ML_V1.txt`

## Required user action

1. Pull `main` in GitHub Desktop.
2. Double-click repository-root `RUN_GOLD_ML_V1_NEXT.bat`.
3. Upload the selected `UPLOAD_THIS_GOLD_ML_V1.txt`.

## Still forbidden

- rescue tuning after zero survivors;
- changing the 36-cell grid or gates;
- using 2024, 2025 or 2026 to retune;
- modifying or replacing the frozen nine;
- same-lineage portfolio pooling;
- automatic accumulation, promotion or registration;
- live signal, Discord, AI API or MT5 order.
