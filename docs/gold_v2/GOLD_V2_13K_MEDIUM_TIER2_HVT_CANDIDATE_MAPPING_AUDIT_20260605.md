# GOLD V2 13K MEDIUM TIER2_HVT candidate mapping audit

Created: 2026-06-05

## Scope

This step records the user-approved MEDIUM TIER2_HVT candidate mapping.

Config file:

```text
configs/gold_v2/medium_tier2_hvt_candidate_mapping_20260605.json
```

## Rule

```text
trend_eff96 <= 0.4
ret96 <= -25.0
tr_mean_32 >= 5.105624999999989
```

Feature source:

```text
coreb_refined_rule_ledgers.csv
```

## Limits

This file covers only MEDIUM TIER2_HVT.

It does not complete CoreA, CoreB, or the full MEDIUM rule set.

Final signal dispatch remains disabled.

## 13K audit

13K checks that the config matches the 13H patch preview and keeps safety flags off.
