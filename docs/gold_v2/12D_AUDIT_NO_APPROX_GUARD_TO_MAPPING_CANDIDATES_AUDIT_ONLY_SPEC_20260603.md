# GOLD V2 12D_AUDIT_NO_APPROX_GUARD_TO_MAPPING_CANDIDATES_AUDIT_ONLY specification

Date: 2026-06-03  
Repo: `knitanr-a11y/xauusd-signal-lab`

## 1. Purpose

12D runs after 12C and after `docs/gold_v2/GOLD_V2_COREA_COREB_MEDIUM_SIGNAL_CONDITIONS_NO_APPROX_GUARD_20260603.md` exists.

12D converts the NO_APPROX_GUARD document and 12C candidate inventory into **candidate mapping rows** for audit review only.

It does not create strict live evaluator mappings and does not change any step-12 mapping JSON to `MAPPING_READY`.

## 2. Inputs

Default inputs:

```text
docs/gold_v2/GOLD_V2_COREA_COREB_MEDIUM_SIGNAL_CONDITIONS_NO_APPROX_GUARD_20260603.md
configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json
configs/gold_v2/frozen_coreA_fold4_ABC_CAP5_rules_20260603.json
configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json
configs/gold_v2/frozen_medium_rules_20260603.json
configs/gold_v2/live_evaluator_mapping_coreA_20260603.json
configs/gold_v2/live_evaluator_mapping_coreB_20260603.json
configs/gold_v2/live_evaluator_mapping_medium_20260603.json
Files/FX_OUTPUTS/gold_v2_candidate_rule_definition_inventory_audit_only/gold_v2_candidate_text_samples.csv
Files/FX_OUTPUTS/gold_v2_candidate_rule_definition_inventory_audit_only/gold_v2_candidate_variant_inventory.csv
```

## 3. Output folder

Default:

```text
Files/FX_OUTPUTS/gold_v2_no_approx_guard_mapping_candidates_audit_only
```

Generated files:

```text
GOLD_V2_NO_APPROX_GUARD_MAPPING_CANDIDATES_AUDIT_ONLY_REPORT.md
gold_v2_no_approx_guard_mapping_candidates_summary.json
gold_v2_no_approx_mapping_candidate_conditions.csv
gold_v2_no_approx_mapping_candidate_blocking_gaps.csv
gold_v2_no_approx_component_candidate_packets.csv
gold_v2_no_approx_guard_candidate_audit_checks.csv
candidate_packet_HIGH_A_CoreA_fold4_ABC_CAP5.json
candidate_packet_HIGH_B_CoreB_RR125_BUY_CONFLUENCE.json
candidate_packet_MEDIUM_REFINED_FEATURE_GATES.json
```

## 4. What 12D produces

### 4.1 Candidate condition rows

12D writes rows such as:

```text
component
candidate_group
condition_id
field
operator
value
source
candidate_status
blocking_dependency
raw_text
```

These rows are candidates only.

### 4.2 Blocking gaps

12D keeps unresolved items separate as blocking gaps, for example:

```text
CoreA_A_gate requires source definition
CoreB RR1 source BUY rule universe requires freezing
CoreB same_count source universe requires freezing
MEDIUM high arbitration required
MEDIUM PROBE direction unmapped
MEDIUM Tier2 static unmapped
```

A candidate row does not override a blocking gap.

## 5. Expected component behavior

### 5.1 CoreA

12D may extract candidate guard conditions for:

```text
B: regime == MID_MIXED
B: trend_eff96 >= 0.633155
B: rr >= 1.5
C: range96 >= 100.43
C: range96 <= 117.86
```

But CoreA A gate remains blocking unless the strict source definition for:

```text
10-day lookback
tail_hard
top5
all consensus
stack allowed only KEEP
otherwise REJECT
```

is frozen as explicit executable predicates.

### 5.2 CoreB

12D may extract candidate fixed conditions:

```text
direction == BUY
same_count >= 15
TP width = 1.25 * SL width
sizing == CAP3
lot_multiplier_candidate == 1.0
```

It may also parse 12C `base_condition` / `added_filter_text` text samples into field/operator/value rows.

But CoreB remains blocking until:

```text
RR1.0 BUY source rule universe is frozen
same_count source rule universe is frozen
SL source / variant selector is frozen
```

### 5.3 MEDIUM

12D may extract candidate guard conditions for RANGE96_REFINED, VOL_TRMEAN32_REFINED, and TIER2_HVT.

MEDIUM remains blocked as final signal until:

```text
CoreA/CoreB arbitration is explicitly mapped
PROBE direction is resolved
Tier2 static conditions are explicit
```

## 6. Non-negotiable guards

12D must not:

```text
connect step 13
write live_evaluator_mapping_* as MAPPING_READY
turn candidate rows into live signals
use entry_time matches as signal source
infer fold4_rules from ledgers
infer RR1.0 source rules from candidate_id/origin_id only
send Discord notifications
place MT5 orders
call AI API
call live hooks
notify on NO_SIGNAL
```

## 7. BAT specification

BAT:

```text
scripts\gold_v2_runtime\bat\12D_AUDIT_NO_APPROX_GUARD_TO_MAPPING_CANDIDATES_AUDIT_ONLY.bat
```

Executed command:

```text
python scripts\gold_v2_runtime\audit_gold_v2_no_approx_guard_to_mapping_candidates_audit_only.py %*
```

Exit codes:

| Code | Meaning |
|---:|---|
| 0 | Candidate audit completed and outputs were written. |
| 2 | Required guard doc / mapping JSON missing, policy safety failure, or output failure. |
| other | Unexpected runtime error. |

## 8. Expected current status

Expected output status:

```text
NO_APPROX_GUARD_MAPPING_CANDIDATES_READY_BUT_NOT_STRICT_MAPPING
```

Expected safety state:

```text
live_evaluator_connection_allowed=false
final_signal_allowed=false
```

## 9. Next step after 12D

After 12D, review:

```text
gold_v2_no_approx_mapping_candidate_conditions.csv
gold_v2_no_approx_mapping_candidate_blocking_gaps.csv
candidate_packet_HIGH_A_CoreA_fold4_ABC_CAP5.json
candidate_packet_HIGH_B_CoreB_RR125_BUY_CONFLUENCE.json
candidate_packet_MEDIUM_REFINED_FEATURE_GATES.json
```

If and only if enough source-of-truth information exists, a later explicit freezing step may author strict `live_evaluator_mapping.conditions` and then rerun step 12.

Do not implement signal-producing step 13 while any blocking gap remains.
