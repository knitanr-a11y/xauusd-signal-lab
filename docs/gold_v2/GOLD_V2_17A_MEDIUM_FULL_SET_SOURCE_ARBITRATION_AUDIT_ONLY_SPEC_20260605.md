# GOLD V2 17A MEDIUM full-set source arbitration audit-only spec

Created: 2026-06-05

## Purpose

16B recommended 17A as the next step. MEDIUM_TIER2_HVT has candidate mapping/load-smoke status, but the full MEDIUM set is still incomplete.

17A inventories available MEDIUM source ledgers and classifies each component as:

```text
READY_CANDIDATE_MAPPING
HISTORICAL_SOURCE_ONLY
NEEDS_REPLAY_PARITY
MISSING_SOURCE
```

This step does not enable any live path.

## Inputs

```text
FX_OUTPUTS/gold_v2_16b_next_chat_handoff_and_safe_roadmap_audit_only/gold_v2_16b_handoff_summary.json
FX_OUTPUTS/gold_v2_13l_medium_tier2_hvt_candidate_mapping_load_smoke_audit/gold_v2_13l_load_smoke_summary.json
FX_OUTPUTS/gold_v2_coreb_refined_probe_outputs/coreb_refined_rule_ledgers.csv
FX_OUTPUTS/gold_v2_coreb_refined_probe_outputs/coreb_refined_combined_ledgers.csv
configs/gold_v2/medium_tier2_hvt_candidate_mapping_20260605.json
```

## Outputs

```text
FX_OUTPUTS/gold_v2_17a_medium_full_set_source_arbitration_audit_only
```

```text
GOLD_V2_17A_MEDIUM_FULL_SET_SOURCE_ARBITRATION_AUDIT_ONLY_REPORT.md
gold_v2_17a_input_audit.csv
gold_v2_17a_medium_component_inventory.csv
gold_v2_17a_medium_arbitration_matrix.csv
gold_v2_17a_blockers.csv
gold_v2_17a_medium_full_set_source_arbitration_summary.json
```

## Expected status

```text
MEDIUM_FULL_SET_SOURCE_ARBITRATION_BUILT_AUDIT_ONLY_PARTIAL_READY
```

## Prohibitions

No Discord, no MT5, no AI API, no live hook, no final signal, no live enablement.
