# GOLD V2 12F_FREEZE_COREB_LIVE_EVALUATOR_SOURCE_DEFINITION_AUDIT_ONLY specification

Date: 2026-06-03  
Repo: `knitanr-a11y/xauusd-signal-lab`

## 1. Purpose

12F runs after 12E.

12E showed:

```text
CoreB source_rule_candidate_count = 33
CoreB freeze_ready_rule_candidate_count = 33
CoreB blocking_gap_count = 0
```

12F freezes a CoreB-only explicit source definition JSON from the 12E audit outputs.

This is still **audit-only**. The frozen source definition is not a live evaluator mapping and does not connect step 13.

## 2. Inputs

Default inputs:

```text
configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json
configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json
configs/gold_v2/live_evaluator_mapping_coreB_20260603.json
Files/FX_OUTPUTS/gold_v2_coreb_source_rule_universe_freeze_readiness_audit_only/gold_v2_coreb_source_rule_universe_freeze_readiness_summary.json
Files/FX_OUTPUTS/gold_v2_coreb_source_rule_universe_freeze_readiness_audit_only/gold_v2_coreb_source_rule_universe_candidates.csv
Files/FX_OUTPUTS/gold_v2_coreb_source_rule_universe_freeze_readiness_audit_only/gold_v2_coreb_source_rule_condition_rows.csv
Files/FX_OUTPUTS/gold_v2_coreb_source_rule_universe_freeze_readiness_audit_only/gold_v2_coreb_variant_policy_audit.csv
Files/FX_OUTPUTS/gold_v2_coreb_source_rule_universe_freeze_readiness_audit_only/gold_v2_coreb_same_count_derivation_audit.csv
Files/FX_OUTPUTS/gold_v2_coreb_source_rule_universe_freeze_readiness_audit_only/gold_v2_coreb_freeze_readiness_gaps.csv
```

## 3. Output files

### 3.1 Config output

```text
configs/gold_v2/frozen_coreB_live_evaluator_source_definition_20260603.json
```

This file is a frozen source-definition candidate for a later mapping step.

It must include:

```text
status = FROZEN_COREB_LIVE_EVALUATOR_SOURCE_DEFINITION_READY_AUDIT_ONLY
component = HIGH_B_CoreB_RR125_BUY_CONFLUENCE
source_policy = FROZEN_GOLD_V2_COREB_RR125_BUY_CONFLUENCE_20260603
rule_universe_count = 33
same_count_min = 15
direction = BUY
rr_policy = TP = 1.25 * SL
sizing = CAP3
live_evaluator_mapping_ready = false
final_signal_allowed = false
step12_rerun_required = true
```

### 3.2 Audit output folder

Default:

```text
Files/FX_OUTPUTS/gold_v2_coreb_live_evaluator_source_definition_freeze_audit_only
```

Generated files:

```text
GOLD_V2_COREB_LIVE_EVALUATOR_SOURCE_DEFINITION_FREEZE_AUDIT_ONLY_REPORT.md
gold_v2_coreb_live_evaluator_source_definition_freeze_summary.json
gold_v2_coreb_live_evaluator_source_definition_rules.csv
gold_v2_coreb_live_evaluator_source_definition_conditions.csv
gold_v2_coreb_live_evaluator_source_definition_policy_checks.csv
```

## 4. Frozen rule structure

Each CoreB rule definition contains:

```text
rule_id
candidate_id
origin_id
direction
variant
tp_pips
sl_pips
rr
base_condition predicates
added_filter_text predicates
raw_signal_row_count
```

Each predicate contains:

```text
field
operator
value
source_column
raw_text
```

## 5. Safety requirements

12F must not:

```text
set live_evaluator_mapping_ready=true
set final_signal_allowed=true
write live_evaluator_mapping_coreB_20260603.json as MAPPING_READY
connect step 13
create final signals
send Discord notifications
place MT5 orders
call AI API
call live hooks
notify on NO_SIGNAL
```

## 6. Success condition

12F succeeds if:

```text
12E summary status is COREB_SOURCE_RULE_UNIVERSE_FREEZE_READY_AUDIT_ONLY
12E blocking_gap_count == 0
all source rule candidates have freeze_ready_candidate == true
all condition rows are readable
policy safety is OK
config JSON and audit outputs are written
```

## 7. Expected output status

```text
FROZEN_COREB_LIVE_EVALUATOR_SOURCE_DEFINITION_READY_AUDIT_ONLY
```

## 8. Next step after 12F

After 12F, do not connect step 13.

The next correct step is to update/rerun step 12 mapping so it can consume:

```text
configs/gold_v2/frozen_coreB_live_evaluator_source_definition_20260603.json
```

and determine whether CoreB can move from:

```text
MAPPING_BLOCKED_UNMAPPED_CONDITION
```

to a non-signal mapping-ready audit state.

CoreA and MEDIUM final-signal blocking still remain unless separately resolved.
