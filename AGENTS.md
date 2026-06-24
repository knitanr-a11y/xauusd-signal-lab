# Repository Agent Instructions

## GOLD_ML_V1

1. Use only the GOLD_ML_V1 namespace and its clean-rebuild contracts.
2. Do not use quarantined legacy GOLD logic or derived artifacts. Only the explicitly authorized raw candle files are allowed.
3. Preserve MT5 server timestamps and bar-close availability.
4. Candidate logic is immutable. Changed logic requires a new ID. Portfolio records are separate.
5. Apply the broad-search, coverage-first loss-subtraction, and causal structural-feature policies under `config/gold_ml_v1/`.
6. Apply `config/gold_ml_v1/provisional_stack_admission_gate_20260624.json`. Marginal PF, tiny samples, or merely positive totals remain research-only.
7. The active provisional stack is `config/gold_ml_v1/provisional_candidate_stack_20260624.json` and currently contains only:
   - GML1-PROV-007
   - GML1-PROV-008
   - GML1-PROV-010
   - GML1-PROV-015
8. GML1-PROV-002 is reference-only. GML1-PROV-013, PROV-016, PROV-018, and PROV-019 are not active accumulated candidates.
9. Historical audit files remain available after demotion.
10. Local replay and fresh prospective confirmation are required before registration.
11. The 2026 sample is diagnostic only and cannot be used for retuning. Fresh prospective confirmation begins after MT5 server close time `2026-06-23 18:15:00`.
12. Remain audit-only. No live activation or automatic promotion.
13. Never claim completion until outputs are inspected.

Current status:

`GOLD_ML_V1_001_FOUR_ACTIVE_PROVISIONAL_ENTRIES_STRICT_GATE_ACTIVE`

Next phase:

`SEARCH_ONLY_MATERIAL_EDGE_AND_REJECT_MARGINAL_RESULTS`
