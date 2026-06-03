# GOLD V2 12B_UNMAPPED_RULE_SOURCE_DEFINITION_AUDIT_ONLY specification

Date: 2026-06-03  
Repo: `knitanr-a11y/xauusd-signal-lab`

## 1. Purpose

12B is an audit-only step after `12_MAP_FROZEN_RULES_TO_LIVE_EVALUATOR_AUDIT_ONLY`.

Step 12 correctly blocks CoreA/CoreB with `UNMAPPED_CONDITION`. 12B does not remove that block. It only investigates whether the frozen manifests and their referenced source CSV ledgers contain enough explicit rule-definition evidence to later create a proper `live_evaluator_mapping`.

This step is for **UNMAPPED resolution audit**, not live evaluator execution.

## 2. Non-negotiable guards

- Do not use old GOLD / DISC8.
- Do not use historical `entry_time` matches as live signal rules.
- Do not infer `fold4_rules`, `ABC`, `RR1.0-derived BUY rules`, `same_count>=15`, or TP/SL selectors from ledger hits alone.
- Do not create or update the step-12 mapping JSON as `MAPPING_READY`.
- Do not connect step 13.
- Do not send Discord notifications.
- Do not place MT5 orders.
- Do not call AI API.
- Do not call live hooks.
- NO_SIGNAL notification policy remains `DO_NOT_NOTIFY_ON_NO_SIGNAL`.

## 3. Inputs

### 3.1 Step 12 mapping JSON

Default config mapping files:

```text
configs/gold_v2/live_evaluator_mapping_coreA_20260603.json
configs/gold_v2/live_evaluator_mapping_coreB_20260603.json
configs/gold_v2/live_evaluator_mapping_medium_20260603.json
```

### 3.2 Frozen manifests

```text
configs/gold_v2/frozen_coreA_fold4_ABC_CAP5_rules_20260603.json
configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json
configs/gold_v2/frozen_medium_rules_20260603.json
```

### 3.3 Source CSV ledgers referenced by frozen manifests

The script reads the `source_files[].path` entries inside the frozen manifests.

These CSVs are audit evidence only. They must not be converted into signal rules unless explicit live-evaluable definitions are present.

Expected source paths include:

```text
Files/FX_OUTPUTS/gold_v2_ABC_stack_cap_2025_2026_validation_outputs/abc_stack_cap_2025_fold4_cluster_ledger.csv
Files/FX_OUTPUTS/gold_v2_ABC_stack_cap_2025_2026_validation_outputs/abc_stack_cap_2026_cluster_ledger.csv
Files/FX_OUTPUTS/gold_v2_rr125_second_core_probe_outputs/rr125_top_ledgers.csv
Files/FX_OUTPUTS/gold_v2_rr125_second_core_probe_outputs/rr125_raw_signal_ledger.csv
Files/FX_OUTPUTS/gold_v2_coreb_refined_probe_outputs/coreb_refined_rule_ledgers.csv
```

## 4. Output folder

Default:

```text
Files/FX_OUTPUTS/gold_v2_unmapped_rule_source_definition_audit_only
```

Generated files:

```text
GOLD_V2_UNMAPPED_RULE_SOURCE_DEFINITION_AUDIT_ONLY_REPORT.md
gold_v2_unmapped_rule_source_definition_summary.json
gold_v2_unmapped_condition_resolution_audit.csv
gold_v2_unmapped_source_column_evidence.csv
gold_v2_unmapped_candidate_text_samples.csv
gold_v2_unmapped_source_file_audit.csv
```

## 5. Resolution statuses

12B uses strict statuses.

| Status | Meaning | Can live evaluator connect? |
|---|---|---|
| `RESOLVED_EXPLICIT_MAPPING_FOUND` | An explicit `live_evaluator_mapping.conditions` block exists with concrete field/operator/value predicates. | Not automatically; rerun 12 and pass all gates first. |
| `CANDIDATE_EVIDENCE_ONLY` | Source CSV contains useful evidence columns/text, but not enough strict live-evaluator predicates. | No |
| `UNRESOLVED_SOURCE_DEFINITION_MISSING` | The necessary source definition is not present in frozen manifests or ledgers. | No |
| `SOURCE_FILE_MISSING_OR_UNREADABLE` | Required local source files cannot be read. | No |
| `NOT_APPLICABLE` | No blocking unmapped condition exists for that component. | No automatic connection |

Current expected result is `CANDIDATE_EVIDENCE_ONLY` or `UNRESOLVED_SOURCE_DEFINITION_MISSING`, because CoreA/CoreB frozen manifests are textual and step 12 has correctly blocked them.

## 6. Condition-specific audit targets

### 6.1 CoreA

Blocking items from step 12:

```text
fold4_rules
ABC_entry_gate
A_CAP5_BC_CAP3_classification
variant_defined_tp_sl_policy
```

12B checks whether the CoreA frozen manifest or its source CSVs contain explicit live predicates for:

- fold4 rule definitions
- A/B/C gate predicates
- A/B/C sizing or classification predicates
- variant selector and TP/SL selection predicates

Ledger columns such as `signal_ABC`, `is_A`, `is_B_rr15_fixed`, `is_C_fixed`, `top_variant`, or `top_entry_time` are only evidence. They are not enough by themselves.

### 6.2 CoreB

Blocking items from step 12:

```text
RR1_source_BUY_rule_definitions
same_count_confluence_derivation
rr125_tp_sl_conversion
```

12B checks whether the CoreB frozen manifest or source CSVs contain explicit live predicates for:

- selected RR1 BUY rule definitions
- same-count derivation universe and confluence computation
- RR125 TP/SL conversion and live SL/variant selector

Columns such as `base_condition`, `added_filter_text`, `same_count`, `source_rule_count`, `tp_pips`, `sl_pips`, `rr`, or `variant` are useful evidence. They are not automatically live-evaluable mapping.

## 7. BAT specification

BAT:

```text
scripts\gold_v2_runtime\bat\12B_AUDIT_UNMAPPED_RULE_SOURCE_DEFINITIONS_AUDIT_ONLY.bat
```

Executed command:

```text
python scripts\gold_v2_runtime\audit_gold_v2_unmapped_rule_source_definitions_audit_only.py %*
```

Exit codes:

| Code | Meaning |
|---:|---|
| 0 | Audit completed and outputs were written. Unresolved conditions may still remain. |
| 2 | Required JSON/source input missing, policy unsafe, or audit output cannot be produced. |
| Other | Unexpected Python/runtime error. |

Because 12B is an audit report, unresolved CoreA/CoreB conditions do **not** make the BAT fail. The report status and `live_evaluator_connection_allowed=false` are the safety gate.

## 8. Success conditions

12B is successful when:

1. Step-12 mapping JSON files are readable.
2. Frozen manifests are readable.
3. Policy/external action safety remains off.
4. Source CSV ledger accessibility and SHA status are recorded.
5. Every blocking `UNMAPPED_CONDITION` is classified as:
   - explicit mapping found,
   - candidate evidence only,
   - unresolved source definition missing,
   - or source file unreadable.
6. Output report/CSV/JSON files are written.
7. No external side effects occur.

## 9. Stop / no-go condition after 12B

Even if 12B finds useful evidence columns, do not connect live evaluator until a later step explicitly freezes live-evaluable predicates and step 12 no longer reports blocking `UNMAPPED_CONDITION`.

Do not implement signal-producing step 13 while:

```text
live_evaluator_connection_allowed=false
blocking_unmapped_condition_count > 0
```

## 10. Expected current result

Given the current step-12 report:

```text
CoreA: 4 blocking UNMAPPED_CONDITION
CoreB: 3 blocking UNMAPPED_CONDITION
MEDIUM: feature gates mapped, final signal blocked
```

Expected 12B output is:

```text
status=UNRESOLVED_SOURCE_DEFINITION_REMAINS
live_evaluator_connection_allowed=false
```

The audit should likely show that source ledgers contain evidence columns, but CoreA/CoreB still lack strict explicit frozen live-evaluator predicates.
