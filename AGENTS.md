# Repository Agent Instructions

## GOLD_ML_V1 clean rebuild

When a task concerns `GOLD_ML_V1`, the new machine-learning rebuild, obey these rules before any repository search or implementation:

1. Read only:
   - `AGENTS.md`
   - `docs/gold_ml_v1/START_HERE_GOLD_ML_V1_CLEAN_REBUILD_20260624.md`
   - `config/gold_ml_v1/project_contract.json`
   - files subsequently created under the `gold_ml_v1` namespace.
2. Do not search, read, reference, compare against, inherit from, import, summarize, or fall back to:
   - `docs/gold_v3/**`
   - `scripts/gold_v3_runtime/**`
   - `models/gold_v3/**`
   - `tests/gold_v3/**`
   - `FX_OUTPUTS/gold_v3/**`
   - any old GOLD stage, model, scaler, feature list, label, threshold, candidate, portfolio, metric, output, runtime state, bootstrap, journal, watch, or handoff.
3. Do not delete, rewrite, move, or rename the old files. They are quarantined by policy.
4. Put new repository work only under:
   - `docs/gold_ml_v1/`
   - `config/gold_ml_v1/`
   - `scripts/gold_ml_v1/`
   - `models/gold_ml_v1/`
   - `tests/gold_ml_v1/`
5. The user objective is to accumulate multiple independently validated high-win-rate candidates.
6. Candidate records are append-only and immutable. Changed logic requires a new candidate ID.
7. Portfolio results are separate from candidate results. Never overwrite candidate trades or metrics with portfolio trades or metrics.
8. Start from fresh raw data under `FX_OUTPUTS/gold_ml_v1/`; do not use an old output namespace as a data source.
9. Remain audit-only until explicit later authorization. Live signals, MT5 orders, Discord, partial close, and automatic promotion remain disabled.
10. Never claim a phase or result is complete until generated outputs are inspected.

Current status:

`GOLD_ML_V1_000_CLEAN_REBUILD_CONTRACT_FROZEN`

Next phase:

`GOLD_ML_V1_001_DATASET_AND_EVALUATION_CONTRACT`
