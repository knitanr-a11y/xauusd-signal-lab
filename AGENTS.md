# Repository Agent Instructions

## GOLD_ML_V1

1. Use only the GOLD_ML_V1 namespace and its clean-rebuild contracts.
2. Do not use quarantined legacy GOLD logic or derived artifacts. Only the explicitly authorized raw candle files are allowed.
3. Preserve MT5 server timestamps and bar-close availability.
4. Candidate logic is immutable. Changed logic requires a new ID. Portfolio records are separate.
5. Apply the broad-search, coverage-first loss-subtraction, causal structural-feature, watch-pool, and PF2-refinement policies under `config/gold_ml_v1/`.
6. Marginal PF or merely positive totals do not enter the active stack. PF2 or higher is the refinement target, but count, year stability, cost stress, and genuine later-period filter activations remain mandatory.
7. Low-count structures are preserved and updated prospectively, but are not counted as active candidates.
8. The active provisional stack currently contains only:
   - GML1-PROV-007
   - GML1-PROV-008
   - GML1-PROV-010
   - GML1-PROV-015
9. GML1-PROV-020 reached PF2 historically but is watch-only because its second-stage exclusion fired zero times in the 2026 diagnostic.
10. GML1-WATCH-014-A is a path-shape clustering research watch and is not active because seed stability and interpretability are insufficient.
11. Historical audit files remain available after demotion.
12. Local replay and fresh prospective confirmation are required before registration.
13. The 2026 sample is diagnostic only and cannot be used for retuning. Fresh prospective confirmation begins after MT5 server close time `2026-06-23 18:15:00`.
14. Remain audit-only. No live activation or automatic promotion.
15. Never claim completion until outputs are inspected.

Current status:

`GOLD_ML_V1_001_PF2_REFINEMENT_AND_ALTERNATIVE_PATH_SEARCH_ACTIVE`

Next phase:

`META_LABEL_MAE_MFE_TIME_TO_TARGET_AND_STABLE_REGIME_TRANSITIONS`
