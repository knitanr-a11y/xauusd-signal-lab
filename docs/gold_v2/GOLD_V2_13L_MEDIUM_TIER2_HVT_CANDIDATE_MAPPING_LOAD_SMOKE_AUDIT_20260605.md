# GOLD V2 13L MEDIUM TIER2_HVT candidate mapping load smoke audit

Created: 2026-06-05

## Purpose

13K confirmed that `medium_tier2_hvt_candidate_mapping_20260605.json` matches the 13H patch preview. 13L verifies that the candidate mapping can be loaded and interpreted by a loader-style audit script.

## Scope

Only this candidate is tested:

```text
MEDIUM_TIER2_HVT_RECONCILED_13D3
```

This does not enable CoreA, CoreB, the full MEDIUM set, final signal, Discord, MT5, AI API, or external hooks.

## Inputs

```text
configs/gold_v2/medium_tier2_hvt_candidate_mapping_20260605.json
Files/FX_OUTPUTS/gold_v2_coreb_refined_probe_outputs/coreb_refined_rule_ledgers.csv
```

## Checks

```text
config loads as JSON
schema and scope are expected
rule is enabled for audit evaluator
conditions are parsed by the generic operator loader
TIER2_HVT selected rows == 31
safety flags remain off
CoreA and CoreB remain blocked
```

## Outputs

```text
Files/FX_OUTPUTS/gold_v2_13l_medium_tier2_hvt_candidate_mapping_load_smoke_audit
```

## Expected status

```text
MEDIUM_TIER2_HVT_CANDIDATE_MAPPING_LOAD_SMOKE_PASSED
```
