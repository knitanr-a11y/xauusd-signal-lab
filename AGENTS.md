# Repository Agent Instructions

## GOLD_ML_V1 clean rebuild

When a task concerns `GOLD_ML_V1`, the new machine-learning rebuild, obey these rules before any repository search or implementation:

1. Read only:
   - `AGENTS.md`
   - `docs/gold_ml_v1/START_HERE_GOLD_ML_V1_CLEAN_REBUILD_20260624.md`
   - `config/gold_ml_v1/project_contract.json`
   - `config/gold_ml_v1/data_source_authorization_20260624.json`
   - `config/gold_ml_v1/reproducibility_contract_20260624.json`
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
11. Use the broad search plan in `docs/gold_ml_v1/GOLD_ML_V1_001_BROAD_CANDIDATE_EXPLORATION_PLAN_20260624.md` and `config/gold_ml_v1/candidate_exploration_plan_v1.json`. Search widely, but keep every lane, direction, label, feature set, model, and candidate lineage separate.
12. Use `config/gold_ml_v1/coverage_first_loss_subtraction_policy_20260624.json`: start from broad opportunity coverage, retain negative features as exclusion information, and subtract only composite loser-risk regions. Do not create scarcity by intersecting rare positive conditions too early. Test state-with-cooldown, onset, event, and score-coverage entry modes separately.
13. Use `config/gold_ml_v1/structural_lines_channels_bbands_feature_plan_20260624.json` for causal trendline, confirmed-pivot channel, regression-channel, Donchian, and Bollinger research. Repainting lines and future-confirmed pivots are forbidden.
14. Any result found outside the user's PC is provisional until the same code, configuration, seeds, input hashes, predictions or trade registry, and metrics are reproduced locally under `config/gold_ml_v1/reproducibility_contract_20260624.json`. Commit a one-click Windows runner and exact replay artifacts before asking the user to run it.
15. No candidate may be registered or added to a portfolio before local replay parity passes.
16. The current append-only provisional stack is `config/gold_ml_v1/provisional_candidate_stack_20260624.json` and contains GML1-PROV-002, GML1-PROV-007, and GML1-PROV-008 as separate lineages.
17. GML1-PROV-007 is the H4 overextension and upper-wick loser-filter derivative of GML1-PROV-002.
18. GML1-PROV-008 is the M15 Bollinger-compression loser-filter derivative of GML1-PROV-002, recorded in `config/gold_ml_v1/provisional_bollinger_loss_subtraction_batch005.json`.
19. The 2026 sample has been used for multiple provisional audits and is no longer an untouched final holdout for future candidate selection. Do not retune thresholds on it. Fresh prospective confirmation starts strictly after MT5 server close time `2026-06-23 18:15:00`.
20. Remain audit-only until explicit later authorization. Live signals, MT5 orders, Discord, partial close, and automatic promotion remain disabled.
21. Never claim a phase or result is complete until generated outputs are inspected.

Current status:

`GOLD_ML_V1_001_STRUCTURAL_LINES_CHANNELS_BBANDS_ACTIVE_THREE_PROVISIONAL_STACK_ENTRIES`

Next phase:

`SEARCH_CAUSAL_BBANDS_TRENDLINE_CHANNEL_EVENTS_AND_COMPOSITE_LOSER_EXCLUSIONS`
