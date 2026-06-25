# Repository Agent Instructions

## GOLD_ML_V1

1. Use only the GOLD_ML_V1 namespace and its clean-rebuild contracts.
2. Do not use quarantined legacy GOLD logic or derived artifacts. Only the explicitly authorized raw candle files are allowed.
3. At the start of every new chat or resumed task, read in this order:
   - `AGENTS.md`
   - `config/gold_ml_v1/current_state_snapshot_20260624.json`
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
5. Candidate logic is immutable. Changed logic requires a new ID. Portfolio records are separate.
6. Apply the broad-search, coverage-first loss-subtraction, causal structural-feature, watch-pool, and PF2-refinement policies under `config/gold_ml_v1/`.
7. PF2 or higher is the refinement target, but count, year stability, cost stress, and genuine later-period filter activations remain mandatory.
8. Low-count and demoted WATCH artifacts are preserved for research and prospective review.
9. The accumulated provisional/watch candidate set currently contains nine entries:
   - GML1-PROV-007
   - GML1-PROV-008
   - GML1-WATCH-022-B
   - GML1-PROV-010
   - GML1-PROV-015
   - GML1-PROV-020
   - GML1-WATCH-021-A
   - GML1-WATCH-021-B
   - GML1-WATCH-021-C
10. GML1-WATCH-014-A was demoted to research-only in Batch022 because the reference-seed result was not stable across seeds; its artifacts must remain preserved.
11. GML1-WATCH-022-A remains research-only after Batch020 validation failure.
12. GML1-WATCH-023-A remains research-only after exact deterministic parity passed but 2023 training-sample bootstrap stability failed in Batch022.
13. GML1-WATCH-022-B remains accumulated with the caveat that improvement is concentrated in 2025 and the excluded 2024 subset was profitable.
14. GML1-PROV-020 remains accumulated with the caveat that its second-stage exclusion fired zero times in 2026.
15. GML1-WATCH-021-A/B/C remain accumulated after Batch018 registry and neighborhood validation; authorized raw-candle replay, cost stress and fresh post-cutoff confirmation remain pending.
16. Batch023 registry parity passed, but the first raw replay implementation failed because its ATR method, warmup source, and event eligibility order did not match the frozen research evaluator.
17. The corrected replay is `scripts/gold_ml_v1/replay/nine_candidate_local_replay_v2.py`. ATR14 is the simple arithmetic rolling mean of 14 true ranges, not Wilder recursive ATR.
18. Historical decisions and trade evaluation must use only `gold_v3_2023_2026_*.csv` rows.
19. Exact-overlap-verified `goldsharp_*.csv` rows strictly before the first historical timestamp may be used only as indicator warmup. This prehistory is required for early D1/H4 indicators. Goldsharp rows after the historical maximum must not enter historical replay.
20. Live closed-bar observation must use `goldsharp_*.csv`. Historical files may be used only for indicator warmup and continuity, and historical rows must never emit new live signals.
21. Goldsharp rows at or before the historical maximum are overlap/backfill audit rows only for live operation. New live decisions are allowed only on goldsharp rows strictly after the historical maximum bar-open time.
22. Exact M1 entry and complete-horizon eligibility must be applied before false-to-true onset or H1 event detection.
23. CSV latest rows are closed by contract. Do not drop them as open bars. Keep MT5 server time unchanged.
24. Local historical and live directories were provided out-of-band and must not be committed to the public repository.
25. Install only the verified Batch023 artifact ZIP through the one-command runner or installer before registry parity.
26. Use `scripts/gold_ml_v1/replay/run_batch023_all.bat` for the corrected end-to-end rerun.
27. Do not continue candidate exploration before corrected Batch023 replay and all nine mismatch reports are inspected.
28. Same-lineage candidates do not add independent market edges. Never sum their results as a portfolio.
29. Exact artifact CSVs must come from the verified bundle named in `exact_artifact_locator_20260625.json`; never reconstruct entry timestamps from summary metrics.
30. Historical audit files remain available after demotion.
31. Local replay and fresh prospective confirmation are required before registration.
32. The 2026 sample is diagnostic only and cannot be used for retuning. Fresh prospective confirmation begins after MT5 server close time `2026-06-23 18:15:00`.
33. Remain audit-only. No live activation or automatic promotion.
34. Never claim completion until outputs are inspected.

Current status:

`GOLD_ML_V1_009_NINE_ACCUMULATED_CANDIDATES_BATCH023_REPLAY_V2_COMMITTED_LOCAL_RERUN_REQUIRED_AUDIT_ONLY`

Next phase:

`PULL_REPLAY_V2_RERUN_BATCH023_INSPECT_PROV002_AND_ALL_NINE_PARITY_REPORTS`
