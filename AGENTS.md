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
2. Do not search, read, reference, compare against, inherit from, import, summarize, or fall back to old GOLD V3, GOLD V2, old GOLD, DISC8, Stage41, or any quarantined model, feature, candidate, output, runtime state, handoff, journal, or watch artifact.
3. Exact raw-data exception: the raw candle directory `MQL5\Files\gold_v3_2023_2026\` and root `goldsharp_*.csv` files may be used only under `config/gold_ml_v1/data_source_authorization_20260624.json`.
4. Put new work only under `docs/config/scripts/models/tests/gold_ml_v1`.
5. Candidate records are immutable; changed logic requires a new ID. Portfolio records are separate.
6. Preserve MT5 server timestamps. `time` is bar-open time, latest row is closed, and availability is bar-close time.
7. Use the broad search plan, coverage-first loss-subtraction policy, and causal structural-indicator plan under `config/gold_ml_v1/`.
8. Apply `config/gold_ml_v1/provisional_stack_admission_gate_20260624.json`. A merely positive result, weak PF, or tiny sample is not enough for active-stack admission.
9. Historical audit files must remain available even when a lineage is demoted from the active provisional stack.
10. The active provisional stack is `config/gold_ml_v1/provisional_candidate_stack_20260624.json` and currently contains only:
   - GML1-PROV-002
   - GML1-PROV-007
   - GML1-PROV-008
   - GML1-PROV-010
   - GML1-PROV-013
   - GML1-PROV-015
11. GML1-PROV-016, GML1-PROV-018, and GML1-PROV-019 were demoted after review because their diagnostic strength was insufficient. See `config/gold_ml_v1/provisional_stack_correction_batch010_011_20260624.json`.
12. Any result found outside the user's PC remains provisional until exact local replay passes.
13. The 2026 sample is diagnostic only and cannot be used for retuning. Fresh prospective confirmation starts strictly after MT5 server close time `2026-06-23 18:15:00`.
14. Remain audit-only. Live signals, MT5 orders, Discord, partial close, portfolio activation, and automatic promotion remain disabled.
15. Never claim completion until generated outputs are inspected.

Current status:

`GOLD_ML_V1_001_SIX_ACTIVE_PROVISIONAL_ENTRIES_STRICT_GATE_ACTIVE`

Next phase:

`STRICT_REAUDIT_EXISTING_STACK_AND_SEARCH_ONLY_MATERIAL_EDGE`
