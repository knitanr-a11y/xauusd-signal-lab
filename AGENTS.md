# Repository Agent Instructions

## GOLD_ML_V1

1. Use only the GOLD_ML_V1 namespace and its clean-rebuild contracts.
2. Do not use quarantined legacy GOLD logic or derived artifacts. Only the explicitly authorized raw candle files are allowed.
3. At the start of every new chat or resumed task, read in this order:
   - `AGENTS.md`
   - `config/gold_ml_v1/current_state_snapshot_20260624.json`
   - `config/gold_ml_v1/provisional_candidate_stack_20260624.json`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_20260624.md`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_BATCH016_ADDENDUM_20260624.md`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXACT_INPUTS_ADDENDUM_20260625.md`
   - `config/gold_ml_v1/exact_artifact_locator_20260625.json`
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
16. Batch023 local replay package is ready. Registry SHA, row count, metrics and derivative-parent parity passed. Full raw replay is not complete because authorized historical M1/M15/H1/H4/D1 files were not mounted in the execution environment.
17. Do not continue candidate exploration before Batch023 is run against authorized raw candles and its mismatch report is inspected.
18. Same-lineage candidates do not add independent market edges. Never sum their results as a portfolio.
19. Exact artifact CSVs must come from the verified bundle named in `exact_artifact_locator_20260625.json`; never reconstruct entry timestamps from summary metrics.
20. Historical audit files remain available after demotion.
21. Local replay and fresh prospective confirmation are required before registration.
22. The 2026 sample is diagnostic only and cannot be used for retuning. Fresh prospective confirmation begins after MT5 server close time `2026-06-23 18:15:00`.
23. Remain audit-only. No live activation or automatic promotion.
24. Never claim completion until outputs are inspected.

Current status:

`GOLD_ML_V1_006_NINE_ACCUMULATED_CANDIDATES_BATCH023_LOCAL_REPLAY_PACKAGE_READY_RAW_INPUTS_PENDING_AUDIT_ONLY`

Next phase:

`RUN_BATCH023_ON_AUTHORIZED_RAW_CANDLES_INSPECT_ALL_NINE_DIFFS_THEN_COST_STRESS_AND_NEW_EXPLORATION`
