# Repository Agent Instructions

## GOLD_ML_V1

1. Use only the GOLD_ML_V1 namespace and its clean-rebuild contracts.
2. Do not use quarantined legacy GOLD logic or derived artifacts. Only the explicitly authorized raw candle files are allowed.
3. Preserve MT5 server timestamps and bar-close availability.
4. Candidate logic is immutable. Changed logic requires a new ID. Portfolio records are separate.
5. Apply the broad-search, coverage-first loss-subtraction, causal structural-feature, and watch-pool policies under `config/gold_ml_v1/`.
6. Apply `config/gold_ml_v1/provisional_stack_admission_gate_20260624.json`. Marginal PF or merely positive totals do not enter the active stack.
7. Apply `config/gold_ml_v1/watch_pool_policy_20260624.json`. Low-count structures are preserved and updated prospectively, but are not counted as active candidates.
8. The active provisional stack currently contains only:
   - GML1-PROV-007
   - GML1-PROV-008
   - GML1-PROV-010
   - GML1-PROV-015
9. GML1-PROV-002 is reference-only. GML1-PROV-013, PROV-016, PROV-018, and PROV-019 are not active accumulated candidates.
10. Batch012 alternative-perspective results are recorded in `config/gold_ml_v1/alternative_perspective_batch012_result.json`; its two opening-range structures are watch-only.
11. Historical audit files remain available after demotion.
12. Local replay and fresh prospective confirmation are required before registration.
13. The 2026 sample is diagnostic only and cannot be used for retuning. Fresh prospective confirmation begins after MT5 server close time `2026-06-23 18:15:00`.
14. Remain audit-only. No live activation or automatic promotion.
15. Never claim completion until outputs are inspected.

Current status:

`GOLD_ML_V1_001_FOUR_ACTIVE_ENTRIES_AND_WATCH_POOL_ACTIVE`

Next phase:

`UNSUPERVISED_REGIMES_PATH_SHAPES_SESSION_TRANSITIONS_AND_META_LABELING`
