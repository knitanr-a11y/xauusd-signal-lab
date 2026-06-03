# GOLD V2 12C_CANDIDATE_RULE_DEFINITION_INVENTORY_AUDIT_ONLY specification

Date: 2026-06-03  
Repo: `knitanr-a11y/xauusd-signal-lab`

## 1. Purpose

12C runs after 12B.

12B showed that all seven CoreA/CoreB unmapped conditions are `CANDIDATE_EVIDENCE_ONLY`, not strict explicit live mappings.

12C expands that candidate evidence into concrete inventories:

- source columns and unique values
- text samples from candidate rule-definition columns
- parsed TP/SL/RR candidate variant strings
- numeric statistics for confluence/count/TP/SL fields
- source file accessibility and SHA audit

12C is still audit-only. It does not create live evaluator rules.

## 2. Non-negotiable guards

- Candidate evidence is not a live rule.
- Do not infer CoreA/CoreB rules from historical ledgers.
- Do not convert `entry_time`, `top_entry_time`, or cluster hits into live signals.
- Do not update step-12 mapping JSON to `MAPPING_READY`.
- Do not implement step 13.
- Do not send Discord notifications.
- Do not place MT5 orders.
- Do not call AI API.
- Do not call live hooks.
- NO_SIGNAL policy remains `DO_NOT_NOTIFY_ON_NO_SIGNAL`.

## 3. Inputs

Default inputs:

```text
configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json
configs/gold_v2/frozen_coreA_fold4_ABC_CAP5_rules_20260603.json
configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json
configs/gold_v2/frozen_medium_rules_20260603.json
configs/gold_v2/live_evaluator_mapping_coreA_20260603.json
configs/gold_v2/live_evaluator_mapping_coreB_20260603.json
configs/gold_v2/live_evaluator_mapping_medium_20260603.json
```

The script reads `source_files[].path` from frozen manifests.

## 4. Output folder

Default:

```text
Files/FX_OUTPUTS/gold_v2_candidate_rule_definition_inventory_audit_only
```

Generated files:

```text
GOLD_V2_CANDIDATE_RULE_DEFINITION_INVENTORY_AUDIT_ONLY_REPORT.md
gold_v2_candidate_rule_definition_inventory_summary.json
gold_v2_candidate_component_summary.csv
gold_v2_candidate_source_file_audit.csv
gold_v2_candidate_value_inventory.csv
gold_v2_candidate_variant_inventory.csv
gold_v2_candidate_numeric_stats.csv
gold_v2_candidate_text_samples.csv
gold_v2_candidate_inventory_audit_checks.csv
```

## 5. What each output means

### gold_v2_candidate_value_inventory.csv

Lists unique values and counts for evidence columns found in CoreA/CoreB source ledgers.

Examples:

```text
ruleset
signal_ABC
is_A
is_B_rr15_fixed
is_C_fixed
top_variant
candidate_id
origin_id
base_condition
added_filter_text
same_count
source_rule_count
rr_bucket
```

These values are candidate evidence only.

### gold_v2_candidate_variant_inventory.csv

Parses variant-like text such as:

```text
BUY_TP50_SL25_RR2p0
SELL_TP150_SL150_RR1p0
```

into candidate direction/TP/SL/RR fields.

A parsed variant is still not a live selector unless a later explicit freezing step approves it.

### gold_v2_candidate_numeric_stats.csv

Summarizes candidate numeric fields such as:

```text
same_count
source_rule_count
unique_origins
tp_pips
sl_pips
rr
profit_r
top_score
```

These stats are for audit and design review only.

### gold_v2_candidate_text_samples.csv

Outputs distinct text samples from columns such as:

```text
base_condition
added_filter_text
variant
top_variant
component_desc
ruleset
policy
filter
```

These samples are where explicit rule definitions may or may not exist.

## 6. Expected current status

Expected status:

```text
CANDIDATE_RULE_DEFINITION_INVENTORY_READY_BUT_NOT_STRICT_MAPPING
```

Expected connection status:

```text
live_evaluator_connection_allowed=false
```

## 7. BAT specification

BAT:

```text
scripts\gold_v2_runtime\bat\12C_CANDIDATE_RULE_DEFINITION_INVENTORY_AUDIT_ONLY.bat
```

Executed command:

```text
python scripts\gold_v2_runtime\audit_gold_v2_candidate_rule_definition_inventory_audit_only.py %*
```

Exit codes:

| Code | Meaning |
|---:|---|
| 0 | Inventory audit completed and output files were written. |
| 2 | Required input missing, policy safety failure, or output failure. |
| other | Unexpected runtime error. |

## 8. What 12C does not do

12C does not author `live_evaluator_mapping.conditions`.

A later explicit freezing step is required if the candidate inventory contains enough source-of-truth information.

That later step must:

1. write an explicit candidate definition spec,
2. select only rule definitions that are directly supported by source text/columns,
3. create frozen explicit live predicates,
4. rerun step 12,
5. confirm no blocking `UNMAPPED_CONDITION`,
6. only then consider a non-signal-producing evaluator dry run.

## 9. Stop/no-go condition after 12C

Do not connect step 13 while either remains true:

```text
live_evaluator_connection_allowed=false
blocking_unmapped_condition_count > 0
```

The correct next action after 12C is manual/AI audit of candidate inventory, not live trading.
