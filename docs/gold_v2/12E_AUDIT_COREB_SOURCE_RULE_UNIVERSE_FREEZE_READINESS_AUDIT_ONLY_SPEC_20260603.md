# GOLD V2 12E_COREB_SOURCE_RULE_UNIVERSE_FREEZE_READINESS_AUDIT_ONLY specification

Date: 2026-06-03  
Repo: `knitanr-a11y/xauusd-signal-lab`

## 1. Purpose

12E runs after 12D.

12D produced candidate rows but still reported blocking gaps. CoreB is the most concrete component because it has:

- `base_condition`
- `added_filter_text`
- `candidate_id`
- `origin_id`
- `variant`
- `tp_pips`
- `sl_pips`
- `rr`
- `same_count`
- `source_rule_count`

12E audits whether CoreB's source rule universe can be frozen from the existing RR125 ledgers.

This is still audit-only. It does not create live mappings, does not connect step 13, and does not mark CoreB as `MAPPING_READY`.

## 2. Inputs

Default inputs:

```text
configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json
configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json
configs/gold_v2/live_evaluator_mapping_coreB_20260603.json
```

The script reads `source_files[].path` from CoreB frozen manifest.

Expected source CSVs:

```text
Files/FX_OUTPUTS/gold_v2_rr125_second_core_probe_outputs/rr125_top_ledgers.csv
Files/FX_OUTPUTS/gold_v2_rr125_second_core_probe_outputs/rr125_raw_signal_ledger.csv
```

## 3. Output folder

Default:

```text
Files/FX_OUTPUTS/gold_v2_coreb_source_rule_universe_freeze_readiness_audit_only
```

Generated files:

```text
GOLD_V2_COREB_SOURCE_RULE_UNIVERSE_FREEZE_READINESS_AUDIT_ONLY_REPORT.md
gold_v2_coreb_source_rule_universe_freeze_readiness_summary.json
gold_v2_coreb_source_rule_universe_candidates.csv
gold_v2_coreb_source_rule_condition_rows.csv
gold_v2_coreb_variant_policy_audit.csv
gold_v2_coreb_same_count_derivation_audit.csv
gold_v2_coreb_freeze_readiness_gaps.csv
gold_v2_coreb_source_file_audit.csv
gold_v2_coreb_source_rule_universe_audit_checks.csv
```

## 4. What 12E checks

### 4.1 Source rule universe candidate

12E groups raw signal ledger rows by:

```text
candidate_id
origin_id
direction
variant
tp_pips
sl_pips
rr
rr_bucket
base_condition
added_filter_text
policy
```

It parses `base_condition` and `added_filter_text` into field/operator/value predicates.

A rule candidate is considered freeze-ready only if:

```text
direction == BUY
base_condition parses fully
added_filter_text parses fully, if present
variant/TP/SL/RR are present
source identifiers are present
```

### 4.2 Same-count derivation readiness

12E checks `rr125_top_ledgers.csv` rows for:

```text
top_direction == BUY
same_count >= 15
source_rule_count present
unique_origins present
policy present
```

This does not mean same_count is already a live rule. It only indicates that a later evaluator can derive same_count by counting simultaneous hits over the frozen CoreB rule universe.

### 4.3 Variant and TP/SL policy readiness

12E verifies that the candidate variants satisfy:

```text
BUY only
TP = 1.25 * SL
```

Any non-BUY direction or non-RR1.25 variant remains a blocking gap.

## 5. What 12E does not do

12E must not:

```text
write live_evaluator_mapping_coreB_20260603.json as MAPPING_READY
create final signals
connect step 13
use entry_time matches as live signal source
send Discord notifications
place MT5 orders
call AI API
call live hooks
notify on NO_SIGNAL
```

## 6. Expected status

Expected status when source universe appears freeze-ready but has not been explicitly frozen:

```text
COREB_SOURCE_RULE_UNIVERSE_FREEZE_READY_AUDIT_ONLY
```

Expected safety:

```text
live_evaluator_connection_allowed=false
final_signal_allowed=false
```

## 7. BAT specification

BAT:

```text
scripts\gold_v2_runtime\bat\12E_AUDIT_COREB_SOURCE_RULE_UNIVERSE_FREEZE_READINESS_AUDIT_ONLY.bat
```

Executed command:

```text
python scripts\gold_v2_runtime\audit_gold_v2_coreb_source_rule_universe_freeze_readiness_audit_only.py %*
```

Exit codes:

| Code | Meaning |
|---:|---|
| 0 | Audit completed and outputs were written. |
| 2 | Required input missing, policy unsafe, source CSV unreadable, or output failure. |
| other | Unexpected runtime error. |

## 8. Next step after 12E

If 12E confirms CoreB source universe readiness, the next step is **not step 13**.

The next step is a separate explicit freezing step that writes a frozen CoreB live-evaluator source definition JSON. That future file must be reviewed, then step 12 must be rerun.

Do not connect a signal evaluator while CoreA/CoreB mappings still contain blocking `UNMAPPED_CONDITION`.
