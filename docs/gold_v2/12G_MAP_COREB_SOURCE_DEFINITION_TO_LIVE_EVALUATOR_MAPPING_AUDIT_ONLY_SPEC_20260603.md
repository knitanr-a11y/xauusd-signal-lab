# GOLD V2 12G_MAP_COREB_SOURCE_DEFINITION_TO_LIVE_EVALUATOR_MAPPING_AUDIT_ONLY specification

Date: 2026-06-03  
Repo: `knitanr-a11y/xauusd-signal-lab`

## 1. Purpose

12G runs after 12F.

12F created:

```text
configs/gold_v2/frozen_coreB_live_evaluator_source_definition_20260603.json
```

12G consumes that frozen CoreB source definition and writes a CoreB-only live evaluator mapping JSON in audit-only mode.

This removes CoreB's previous `UNMAPPED_CONDITION` only for CoreB source-rule predicates, same-count derivation, and RR1.25 TP/SL policy.

12G does not connect step 13 and does not create final signals.

## 2. Inputs

Default inputs:

```text
configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json
configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json
configs/gold_v2/frozen_coreB_live_evaluator_source_definition_20260603.json
configs/gold_v2/live_evaluator_mapping_coreB_20260603.json
```

## 3. Outputs

### 3.1 Config output

```text
configs/gold_v2/live_evaluator_mapping_coreB_20260603.json
```

This replaces the previous CoreB blocked mapping file only after writing a full audit copy.

Expected status:

```text
MAPPING_READY_AUDIT_ONLY_FINAL_SIGNAL_BLOCKED
```

Expected safety fields:

```text
live_evaluator_ready = true
live_evaluator_connection_allowed = false
final_signal_allowed = false
component_signal_allowed = false
external_actions all false
```

### 3.2 Audit output folder

Default:

```text
Files/FX_OUTPUTS/gold_v2_coreb_live_evaluator_mapping_from_source_definition_audit_only
```

Generated files:

```text
GOLD_V2_COREB_LIVE_EVALUATOR_MAPPING_FROM_SOURCE_DEFINITION_AUDIT_ONLY_REPORT.md
gold_v2_coreb_live_evaluator_mapping_from_source_definition_summary.json
gold_v2_coreb_live_evaluator_mapping_rules.csv
gold_v2_coreb_live_evaluator_mapping_conditions.csv
gold_v2_coreb_live_evaluator_mapping_policy_checks.csv
live_evaluator_mapping_coreB_20260603.json
previous_live_evaluator_mapping_coreB_20260603.json
```

## 4. Mapping structure

CoreB mapping must include:

```text
component = HIGH_B_CoreB_RR125_BUY_CONFLUENCE
priority = HIGH_B
direction = BUY
rule_universe_count = 33
same_count_min = 15
same_count_derivation.method = count simultaneous hits across mapped CoreB rules
rr_policy.tp_formula = 1.25 * sl_pips
sizing = CAP3
lot_multiplier_candidate = 1.0
mapped_rules[]
mapped_conditions[]
unmapped_conditions = []
```

Each mapped rule contains:

```text
rule_id
candidate_id
origin_id
direction
variant
tp_pips
sl_pips
rr
predicates[]
```

Each predicate contains:

```text
field
operator
value
source_column
raw_text
```

## 5. Stop conditions

12G must stop with exit code 2 if:

```text
policy safety is not audit-only / OFF
CoreB source definition file is missing
CoreB source definition status is not FROZEN_COREB_LIVE_EVALUATOR_SOURCE_DEFINITION_READY_AUDIT_ONLY
rule_universe_count <= 0
any rule has freeze_ready_candidate != true
any rule has direction != BUY
any rule has rr != 1.25
any rule has no predicates
```

## 6. Non-negotiable guards

12G must not:

```text
connect step 13
create final signals
set final_signal_allowed=true
set live_evaluator_connection_allowed=true
send Discord notifications
place MT5 orders
call AI API
call live hooks
notify on NO_SIGNAL
modify CoreA mapping
modify MEDIUM mapping
```

## 7. Why final signal remains blocked

Even if CoreB becomes mapping-ready for audit, final signal remains blocked because:

```text
CoreA still has blocking A gate / fold4 mapping gaps
MEDIUM still requires CoreA/CoreB arbitration
No live evaluator preflight has passed
No external-action approval exists
```

## 8. BAT specification

BAT:

```text
scripts\gold_v2_runtime\bat\12G_MAP_COREB_SOURCE_DEFINITION_TO_LIVE_EVALUATOR_MAPPING_AUDIT_ONLY.bat
```

Executed command:

```text
python scripts\gold_v2_runtime\map_gold_v2_coreb_source_definition_to_live_evaluator_mapping_audit_only.py %*
```

Exit codes:

| Code | Meaning |
|---:|---|
| 0 | CoreB mapping JSON generated in audit-only final-signal-blocked state. |
| 2 | Safety/source validation failed. |
| other | Unexpected runtime error. |

## 9. Next step after 12G

After 12G, rerun a mapping audit / live-rule evaluation audit to verify that CoreB no longer reports the original CoreB `UNMAPPED_CONDITION` items.

Do not connect step 13 until CoreA and arbitration gaps are resolved and a separate preflight passes.
