# GOLD V2 16A portfolio status consolidation audit-only spec

Created: 2026-06-05

## Purpose

13D3-13L completed the MEDIUM_TIER2_HVT candidate-mapping line.
14A-14D completed the CoreB historical-only / live-blocked line.
15A-15C completed the CoreA historical-only / live-blocked line.

16A consolidates the current portfolio status into one audit-only status matrix.

## Inputs

```text
FX_OUTPUTS/gold_v2_13l_medium_tier2_hvt_candidate_mapping_load_smoke_audit/gold_v2_13l_load_smoke_summary.json
FX_OUTPUTS/gold_v2_14c_coreb_historical_sot_candidate_mapping_audit_only/gold_v2_14c_coreb_historical_sot_candidate_mapping_summary.json
FX_OUTPUTS/gold_v2_14d_coreb_original_clustering_candidate_review_audit_only/gold_v2_14d_coreb_original_clustering_candidate_review_summary.json
FX_OUTPUTS/gold_v2_15c_corea_historical_sot_mapping_audit_only/gold_v2_15c_corea_historical_sot_mapping_summary.json
```

## Expected consolidated status

```text
CoreA: historical SOT allowed, live blocked
CoreB: historical SOT allowed, live blocked
MEDIUM_TIER2_HVT: candidate mapping/load smoke passed, live/final signal still off
MEDIUM full set: not complete
final signal: off
Discord/MT5/AI/live hook: off
```

## Outputs

```text
FX_OUTPUTS/gold_v2_16a_portfolio_status_consolidation_audit_only
```

## Prohibitions

No Discord, no MT5, no AI API, no live hook, no final signal, no live enablement.
