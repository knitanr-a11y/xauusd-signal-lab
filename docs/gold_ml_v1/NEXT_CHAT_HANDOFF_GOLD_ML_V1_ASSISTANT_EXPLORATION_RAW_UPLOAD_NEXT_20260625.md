# GOLD_ML_V1 — Assistant-Side Exploration, RAW Upload Next

Date: 2026-06-25

Formal status:

`GOLD_ML_V1_026A_RAW_INPUT_TRANSFER_FOR_ASSISTANT_EXPLORATION_READY_AUDIT_ONLY`

## Corrected workflow

The user clarified that candidate exploration must be executed by ChatGPT first. Local execution is reserved for reproducing an already frozen assistant-side result afterward.

Therefore the previously prepared local Batch024 exploration action must not be used as the discovery run.

Correct order:

1. Package the already frozen M1/M15/H1 raw files without running exploration.
2. Upload the selected ZIP to ChatGPT.
3. ChatGPT validates the exact hashes and executes the full exploration.
4. ChatGPT records all cells, failures, nulls, survivors, multiplicity and year-separated metrics.
5. ChatGPT freezes the accepted research result and its output hashes.
6. Only then create a local one-click reproduction action.
7. Local reproduction must compare its outputs against the assistant-frozen outputs and fail closed on any mismatch.

## Current one-click action

User-facing launcher:

`RUN_GOLD_ML_V1_NEXT.bat`

Current phase BAT:

`scripts/gold_ml_v1/exploration/windows/package_batch024_raw_for_assistant.bat`

This action performs input transfer only. It does not calculate signals, trades, candidates, gates or survivors.

It validates the exact frozen SHA-256 values for:

- `gold_v3_2023_2026_m1.csv`
- `gold_v3_2023_2026_m15.csv`
- `gold_v3_2023_2026_h1.csv`

It then creates:

`outputs/gold_ml_v1/exploration_batch024_data_upload/GOLD_ML_V1_BATCH024_FROZEN_RAW_INPUT.zip`

The root launcher selects that ZIP for upload.

## Exploration cautions that remain mandatory

- Existing frozen nine candidates must not be changed, removed, relabeled or used as rescue targets.
- New logic receives new IDs and remains a separate lineage.
- Search space, execution contract, year split and gates are frozen before seeing results.
- 2023 is exploration only.
- 2024 is validation only and cannot retune.
- 2025 is final test only and cannot retune.
- 2026 is diagnostic only and can never retune.
- All attempted cells, failures, nulls, suppressed events, missing entries and survivors must be retained.
- Best-cell-only reporting and discarded failures are forbidden.
- Lookahead, future exits in features and open/incomplete bars are forbidden.
- Higher-timeframe joins use only confirmed bars available at decision time.
- Same-M1 TP/SL priority remains SL.
- Same-lineage candidates are not independent portfolio edges; PF, profit and trades must not be pooled as if independent.
- A zero-survivor result is valid and cannot trigger rescue tuning.
- All-gate-pass cells remain `RESEARCH_ONLY` until a separate explicit review.
- No automatic accumulation, promotion, registration, live signal, Discord or MT5 order.

## Current blocker

The assistant has the historical audit records and expected hashes but not the actual frozen CSV bytes in the current runtime. The user only needs to transfer the ZIP; the exploration itself will be executed by the assistant after upload.

## Next user action

1. Pull `main` in GitHub Desktop.
2. Double-click repository-root `RUN_GOLD_ML_V1_NEXT.bat`.
3. Upload the selected `GOLD_ML_V1_BATCH024_FROZEN_RAW_INPUT.zip` to ChatGPT.

Do not run the internal phase BAT directly.
