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
8. Low-count structures are preserved and updated prospectively.
9. The accumulated provisional candidate set currently contains six entries:
   - GML1-PROV-007
   - GML1-PROV-008
   - GML1-PROV-010
   - GML1-PROV-015
   - GML1-PROV-020
   - GML1-WATCH-014-A
10. GML1-PROV-020 is accumulated with the caveat that its second-stage exclusion fired zero times in 2026.
11. GML1-WATCH-014-A is accumulated with the caveat that seed stability and human-auditable interpretation remain unresolved.
12. Exact artifact CSVs must come from the verified bundle named in `exact_artifact_locator_20260625.json`; never reconstruct entry timestamps from summary metrics.
13. Historical audit files remain available after demotion.
14. Local replay and fresh prospective confirmation are required before registration.
15. The 2026 sample is diagnostic only and cannot be used for retuning. Fresh prospective confirmation begins after MT5 server close time `2026-06-23 18:15:00`.
16. Remain audit-only. No live activation or automatic promotion.
17. Never claim completion until outputs are inspected.

Current status:

`GOLD_ML_V1_001_EXACT_INPUT_BUNDLE_LOCATED_AUDIT_RUNS_PENDING`

Next phase:

`INSTALL_EXACT_BUNDLE_RUN_BATCH015_PROV020_BATCH016_THEN_MAE_MFE_SHORT_AND_PF2_REFINEMENT`
