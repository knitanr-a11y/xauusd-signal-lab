# Repository Agent Instructions

## GOLD_ML_V1 clean rebuild

When a task concerns `GOLD_ML_V1`, the new machine-learning rebuild, obey these rules before any repository search or implementation:

1. Read only:
   - `AGENTS.md`
   - `docs/gold_ml_v1/START_HERE_GOLD_ML_V1_CLEAN_REBUILD_20260624.md`
   - `config/gold_ml_v1/project_contract.json`
   - `config/gold_ml_v1/data_source_authorization_20260624.json`
   - files subsequently created under the `gold_ml_v1` namespace.
2. Do not search, read, reference, compare against, inherit from, import, summarize, or fall back to:
   - `docs/gold_v3/**`
   - `scripts/gold_v3_runtime/**`
   - `models/gold_v3/**`
   - `tests/gold_v3/**`
   - `FX_OUTPUTS/gold_v3/**`
   - any old GOLD stage, model, scaler, feature list, label, threshold, candidate, portfolio, metric, output, runtime state, bootstrap, journal, watch, or handoff.
3. Exact raw-data exception authorized by the user: the raw candle directory `MQL5\Files\gold_v3_2023_2026\` and the root live `goldsharp_*.csv` files may be used only under `config/gold_ml_v1/data_source_authorization_20260624.json`. The folder name does not authorize any old GOLD logic or derived artifact.
4. Do not delete, rewrite, move, or rename Git-tracked old source files. They are quarantined by policy.
5. A narrow user-authorized maintenance exception exists for local non-Git legacy artifacts only: `scripts/gold_ml_v1/tools/run_archive_legacy_gold_local.bat` may perform opaque ZIP compression, SHA256 recording, ZIP verification, and optional removal after an explicit local confirmation. This exception never permits parsing or using archived content for research, training, comparison, inheritance, fallback, or parity.
6. Put new repository work only under:
   - `docs/gold_ml_v1/`
   - `config/gold_ml_v1/`
   - `scripts/gold_ml_v1/`
   - `models/gold_ml_v1/`
   - `tests/gold_ml_v1/`
7. The user objective is to accumulate multiple independently validated high-win-rate candidates.
8. Candidate records are append-only and immutable. Changed logic requires a new candidate ID.
9. Portfolio results are separate from candidate results. Never overwrite candidate trades or metrics with portfolio trades or metrics.
10. Preserve MT5 server timestamps as raw values. For authorized candle CSVs, `time` is the bar-open time, the latest row is closed, and `bar_close_time = bar_open_time + timeframe duration`. Never discard the latest row as open and never make higher-timeframe data available at its open time.
11. Remain audit-only until explicit later authorization. Live signals, MT5 orders, Discord, partial close, and automatic promotion remain disabled.
12. Never claim a phase or result is complete until generated outputs are inspected.

Current status:

`GOLD_ML_V1_001_DATA_SOURCE_AUTHORIZED_INTAKE_IN_PROGRESS`

Next phase:

`GOLD_ML_V1_001_DATASET_AND_EVALUATION_CONTRACT`
