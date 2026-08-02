# START HERE — GOLD SCALP RETAINED CANDIDATE REGISTRY V1

Status: `GOLD_SCALP_RETAINED_CANDIDATE_REGISTRY_V1_READY_RESEARCH_ONLY`

This branch is the single retrieval point for GOLD candle-only scalp candidates that were explicitly retained for prospective observation, provisional observation, or descriptive research.

## Read order

1. `docs/gold_scalp_retained_candidate_registry/GOLD_SCALP_RETAINED_CANDIDATE_REGISTRY_20260802.md`
2. `config/gold_scalp_retained_candidate_registry/retained_candidate_catalog_20260802.csv`
3. `config/gold_scalp_retained_candidate_registry/retained_candidate_catalog_20260802.json`
4. `config/gold_scalp_retained_candidate_registry/do_not_restore_registry_20260802.csv`
5. `config/gold_scalp_retained_candidate_registry/source_registry_20260802.json`
6. `config/gold_scalp_retained_candidate_registry/current_state_20260802.json`
7. `config/gold_scalp_retained_candidate_registry/next_action_20260802.json`

## Retrieval

All retained records:

```bash
python scripts/gold_scalp_retained_candidate_registry/export_registry.py
```

Only prospective-catalog rows:

```bash
python scripts/gold_scalp_retained_candidate_registry/export_registry.py --tier PROSPECTIVE_CATALOG
```

Only provisional observation leads:

```bash
python scripts/gold_scalp_retained_candidate_registry/export_registry.py --tier PROVISIONAL_OBSERVATION_LEAD
```

JSON output:

```bash
python scripts/gold_scalp_retained_candidate_registry/export_registry.py --format json
```

## Absolute boundary

- Research registry only.
- No candidate in this branch is authorized for Shadow, Discord, MT5 ordering, live trading, promotion, or merge to production.
- Standard accounting boundary remains spread `0.30 USD once`, initial `SL <= 5 USD`, `TP >= 5 USD`, breakeven allowed.
- Rows sharing `dedupe_group` are not independent and must not be summed without exact trade-ledger overlap analysis.
- `V19` and `Challenger C1` remain untouched.
