# Repository Agent Instructions

## GOLD_ML_V1

1. Use only the GOLD_ML_V1 namespace and its clean-rebuild contracts.
2. Do not use quarantined legacy GOLD logic or derived artifacts. Only the explicitly authorized raw candle files are allowed.
3. Preserve MT5 server timestamps and bar-close availability.
4. Candidate logic is immutable. Changed logic requires a new ID. Portfolio records are separate.
5. Apply the broad-search, coverage-first loss-subtraction, causal structural-feature, watch-pool, and PF2-refinement policies under `config/gold_ml_v1/`.
6. PF2 or higher is the refinement target, but count, year stability, cost stress, and genuine later-period filter activations remain mandatory.
7. Low-count structures are preserved and updated prospectively.
8. The accumulated provisional candidate set currently contains six entries:
   - GML1-PROV-007
   - GML1-PROV-008
   - GML1-PROV-010
   - GML1-PROV-015
   - GML1-PROV-020
   - GML1-WATCH-014-A
9. GML1-PROV-020 is accumulated with the caveat that its second-stage exclusion fired zero times in 2026.
10. GML1-WATCH-014-A is accumulated with the caveat that seed stability and human-auditable interpretation remain unresolved.
11. See `config/gold_ml_v1/user_authorized_accumulation_override_20260624.json` for the explicit user-authorized accumulation decision.
12. Historical audit files remain available after demotion.
13. Local replay and fresh prospective confirmation are required before registration.
14. The 2026 sample is diagnostic only and cannot be used for retuning. Fresh prospective confirmation begins after MT5 server close time `2026-06-23 18:15:00`.
15. Remain audit-only. No live activation or automatic promotion.
16. Never claim completion until outputs are inspected.

Current status:

`GOLD_ML_V1_001_SIX_ACCUMULATED_PROVISIONAL_CANDIDATES_WITH_CAVEATS`

Next phase:

`META_LABEL_MAE_MFE_TIME_TO_TARGET_STABLE_REGIME_TRANSITIONS_AND_PF2_REFINEMENT`
