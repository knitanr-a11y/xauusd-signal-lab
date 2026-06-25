# Repository Agent Instructions

## GOLD_ML_V1

1. Use only the GOLD_ML_V1 namespace and its clean-rebuild contracts.
2. Do not use quarantined legacy GOLD logic or derived artifacts. Only the explicitly authorized raw candle files are allowed.
3. At the start of every new chat or resumed task, read in this order:
   - `AGENTS.md`
   - `config/gold_ml_v1/current_state_snapshot_20260624.json`
   - `config/gold_ml_v1/batch023_replay_correction_v3_20260625.json`
   - `config/gold_ml_v1/batch023_replay_correction_v2_20260625.json`
   - `config/gold_ml_v1/batch023_historical_live_source_split_addendum_20260625.json`
   - `config/gold_ml_v1/provisional_candidate_stack_20260624.json`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_20260624.md`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_BATCH016_ADDENDUM_20260624.md`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXACT_INPUTS_ADDENDUM_20260625.md`
   - `config/gold_ml_v1/exact_artifact_locator_20260625.json`
   - `docs/gold_ml_v1/GOLD_ML_V1_BATCH023_NINE_CANDIDATE_LOCAL_REPLAY_20260625.md`
   - `docs/gold_ml_v1/GOLD_ML_V1_RESEARCH_AND_CANDIDATE_IMPLEMENTATION_PLAYBOOK_20260624.md`
   - `docs/gold_ml_v1/OPEN_RESEARCH_INVENTORY_GOLD_ML_V1_20260624.md`
4. Preserve MT5 server timestamps and bar-close availability.
5. Raw CSV `time` is bar-open time. Bar availability is open time plus timeframe duration. Do not reinterpret this contract.
6. Candidate logic is immutable. Changed logic requires a new ID. Portfolio records are separate.
7. Apply the broad-search, coverage-first loss-subtraction, causal structural-feature, watch-pool, and PF2-refinement policies under `config/gold_ml_v1/`.
8. PF2 or higher is the refinement target, but count, year stability, cost stress, and genuine later-period filter activations remain mandatory.
9. Low-count and demoted WATCH artifacts are preserved for research and prospective review.
10. The accumulated provisional/watch candidate set currently contains nine entries:
   - GML1-PROV-007
   - GML1-PROV-008
   - GML1-WATCH-022-B
   - GML1-PROV-010
   - GML1-PROV-015
   - GML1-PROV-020
   - GML1-WATCH-021-A
   - GML1-WATCH-021-B
   - GML1-WATCH-021-C
11. GML1-WATCH-014-A, GML1-WATCH-022-A and GML1-WATCH-023-A remain research-only under their recorded Batch022/Batch020 verdicts.
12. Batch023 registry parity and derivative-parent parity passed.
13. Replay V1-V3 were implementation audits, not candidate failures. V2 showed zero value differences on every common trade. V3 showed the remaining problem was event-contract reconstruction.
14. The current replay is `scripts/gold_ml_v1/replay/nine_candidate_local_replay_v4.py`, launched through `scripts/gold_ml_v1/replay/replay_v4_entry.py` and `scripts/gold_ml_v1/replay/run_batch023_all.bat`.
15. V4 resolves H4 ATR/EMA and M15 Bollinger/percentile implementation only by exact equality to the stored PROV-007 and PROV-008 feature values.
16. V4 audits a finite set of RCI implementation contracts and accepts one only when PROV-007, PROV-008 and WATCH-022-B decision sets all match exactly. Thresholds are never changed.
17. The H1-D1 lane restores the frozen Batch006 behavior: detect the H1 Bollinger event on the complete H1 series, then apply one-position execution. Do not apply the Batch001 onset-order correction to PROV-010.
18. Historical decisions and trade evaluation use only `gold_v3_2023_2026_*.csv` rows.
19. Exact-overlap-verified `goldsharp_*.csv` rows strictly before the first historical timestamp may be used only as indicator warmup. Goldsharp rows after the historical maximum must not enter historical replay.
20. Weekend and broker-maintenance gaps are valid. Time exit uses the last available M1 close inside the wall-clock horizon.
21. Live closed-bar observation uses `goldsharp_*.csv`; historical rows never emit new live signals.
22. CSV latest rows are closed by contract. Keep MT5 server time unchanged.
23. Local source paths must not be committed to the public repository.
24. Use `scripts/gold_ml_v1/replay/run_batch023_all.bat` for the V4 end-to-end rerun.
25. Do not continue candidate exploration before V4 output and all nine parity reports are inspected.
26. Same-lineage candidates do not add independent market edges. Never sum their results as a portfolio.
27. Exact artifact CSVs must come from the verified bundle named in `exact_artifact_locator_20260625.json`.
28. Local replay, cost stress and fresh prospective confirmation are required before registration.
29. The 2026 sample is diagnostic only and cannot be used for retuning.
30. Remain audit-only. No live activation or automatic promotion.
31. Never claim completion until outputs are inspected.

Current status:

`GOLD_ML_V1_011_NINE_ACCUMULATED_CANDIDATES_BATCH023_EXACT_CONTRACT_REPLAY_V4_COMMITTED_LOCAL_RERUN_REQUIRED_AUDIT_ONLY`

Next phase:

`PULL_V4_RERUN_BATCH023_INSPECT_CONTRACT_RESOLUTION_AND_ALL_NINE_PARITY_REPORTS`
