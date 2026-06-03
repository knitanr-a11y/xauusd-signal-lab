# GOLD V2 12_MAP_FROZEN_RULES_TO_LIVE_EVALUATOR_AUDIT_ONLY specification

Date: 2026-06-03  
Repo: `knitanr-a11y/xauusd-signal-lab`

## 1. Purpose

Step 12 creates audit-only live evaluator mapping JSON from the frozen GOLD V2 rule-source manifests produced by step 11.

This step does **not** create live signals and does **not** approximate CoreA/CoreB logic. It only records which frozen conditions are explicitly live-evaluable and which conditions must remain blocked as `UNMAPPED_CONDITION`.

## 2. Non-negotiable guards

- Old GOLD / DISC8 is not used.
- Historical `entry_time` matches, cluster ledgers, or rr125 ledgers must not be treated as live signal rules.
- CoreA/CoreB textual rule names such as `fold4_rules`, `ABC`, `RR1.0-derived BUY rules`, or `same_count>=15` are not enough to implement a live evaluator.
- If explicit live-evaluable predicates are missing, the mapping status must be blocked with `UNMAPPED_CONDITION`.
- No Discord notification is sent.
- No MT5 order is placed.
- No AI API is called.
- No live hook is called.
- NO_SIGNAL notification policy remains `DO_NOT_NOTIFY_ON_NO_SIGNAL`.

## 3. Inputs

### 3.1 Policy JSON

Default:

```text
configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json
```

Required safety flags:

```json
{
  "safety": {
    "ai_api_enabled": false,
    "discord_enabled": false,
    "mt5_order_enabled": false,
    "live_hook_enabled": false,
    "audit_only": true
  }
}
```

The policy JSON is used for safety, priority, lot, confluence, and MEDIUM priority order metadata.

### 3.2 Frozen CoreA JSON

Default:

```text
configs/gold_v2/frozen_coreA_fold4_ABC_CAP5_rules_20260603.json
```

Expected source-of-truth manifest fields:

- `policy_id`
- `status`
- `component`
- `source_of_truth_type`
- `approximation_allowed`
- `external_actions_allowed`
- `definition`
- `source_files`

CoreA can only become `MAPPING_READY` if the frozen manifest contains an explicit evaluator mapping block such as `live_evaluator_mapping.conditions` with concrete fields/operators/values. The current textual manifest shape is expected to remain blocked.

### 3.3 Frozen CoreB JSON

Default:

```text
configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json
```

Expected source-of-truth manifest fields:

- `policy_id`
- `status`
- `component`
- `source_of_truth_type`
- `approximation_allowed`
- `external_actions_allowed`
- `definition`
- `source_files`

CoreB can only become `MAPPING_READY` if the frozen manifest contains explicit selected-rule predicates, live same-count derivation, and TP/SL source selection. The current textual RR125 manifest shape is expected to remain blocked.

### 3.4 Frozen MEDIUM JSON

Default:

```text
configs/gold_v2/frozen_medium_rules_20260603.json
```

Expected explicit feature conditions under:

```text
definition.rules[].conditions
```

Supported condition suffixes:

| Suffix | Live operator |
|---|---|
| `_min` | `>=` |
| `_max` | `<=` |
| `_eq` | `==` |

MEDIUM feature gates may be mapped, but final signal eligibility remains blocked until CoreA/CoreB arbitration is explicitly mapped.

### 3.5 Source CSVs referenced by frozen manifests

The script does not use source CSV rows to create rules. It records and optionally verifies manifest source-file fingerprints only.

Expected referenced CSVs from step 11:

```text
Files/FX_OUTPUTS/gold_v2_ABC_stack_cap_2025_2026_validation_outputs/abc_stack_cap_2025_fold4_cluster_ledger.csv
Files/FX_OUTPUTS/gold_v2_ABC_stack_cap_2025_2026_validation_outputs/abc_stack_cap_2026_cluster_ledger.csv
Files/FX_OUTPUTS/gold_v2_rr125_second_core_probe_outputs/rr125_top_ledgers.csv
Files/FX_OUTPUTS/gold_v2_rr125_second_core_probe_outputs/rr125_raw_signal_ledger.csv
Files/FX_OUTPUTS/gold_v2_coreb_refined_probe_outputs/coreb_refined_rule_ledgers.csv
```

These remain audit evidence only and are not used as live rule substitutions.

## 4. Outputs

### 4.1 Config mapping JSON

Default output directory:

```text
configs/gold_v2
```

Files:

```text
configs/gold_v2/live_evaluator_mapping_coreA_20260603.json
configs/gold_v2/live_evaluator_mapping_coreB_20260603.json
configs/gold_v2/live_evaluator_mapping_medium_20260603.json
```

### 4.2 Audit output directory

Default:

```text
Files/FX_OUTPUTS/gold_v2_live_evaluator_mapping_audit_only
```

Files:

```text
live_evaluator_mapping_coreA_20260603.json
live_evaluator_mapping_coreB_20260603.json
live_evaluator_mapping_medium_20260603.json
gold_v2_live_evaluator_mapping_summary.json
gold_v2_live_evaluator_mapping_status.csv
gold_v2_live_evaluator_mapping_audit_checks.csv
gold_v2_live_evaluator_mapping_unmapped_conditions.csv
GOLD_V2_LIVE_EVALUATOR_MAPPING_AUDIT_ONLY_REPORT.md
```

## 5. Success conditions

Step 12 is successful as an audit if:

1. Policy JSON exists and safety flags are all audit-only safe.
2. Frozen JSON files exist and parse.
3. Each frozen JSON preserves `approximation_allowed=false` and `external_actions_allowed=false`.
4. Outputs are written to both config and audit directories.
5. Any mapping-incomplete CoreA/CoreB condition is explicitly listed as `UNMAPPED_CONDITION`.
6. No external side effect occurs.

The default command exits with code `2` when blocking `UNMAPPED_CONDITION` exists. This is intentional because the mapping must not be consumed by a live evaluator. Use `--allow-unmapped-exit-zero` only when a report-only CI/pass-through run is needed.

## 6. Stop conditions

The script must stop with a non-zero code when any of the following occurs:

- Policy JSON is missing or fails safety checks.
- Frozen JSON is missing or invalid.
- Frozen manifest status is not `FROZEN_RULE_SOURCE_READY`.
- `approximation_allowed` is not false.
- `external_actions_allowed` is not false.
- CoreA/CoreB lacks explicit live-evaluable predicates.
- Any condition key is not supported by the strict mapping schema.
- Any blocking `UNMAPPED_CONDITION` remains.

## 7. Implemented files

```text
scripts/gold_v2_runtime/map_gold_v2_frozen_rules_to_live_evaluator_audit_only.py
scripts/gold_v2_runtime/bat/12_MAP_FROZEN_RULES_TO_LIVE_EVALUATOR_AUDIT_ONLY.bat
docs/gold_v2/12_MAP_FROZEN_RULES_TO_LIVE_EVALUATOR_AUDIT_ONLY_SPEC_20260603.md
```

## 8. Execution order

Run in this order:

```text
scripts\gold_v2_runtime\bat\11_FREEZE_RULE_SOURCES_AUDIT_ONLY.bat
scripts\gold_v2_runtime\bat\10_EVALUATE_LIVE_RULES_AUDIT_ONLY.bat
scripts\gold_v2_runtime\bat\12_MAP_FROZEN_RULES_TO_LIVE_EVALUATOR_AUDIT_ONLY.bat
```

Expected current result:

- 10番: CoreA/CoreB should be `RULE_SOURCE_PRESENT_BUT_EVALUATOR_NOT_IMPLEMENTED` when frozen JSON exists locally.
- 12番: CoreA/CoreB should be blocked as `MAPPING_BLOCKED_UNMAPPED_CONDITION` unless future frozen JSON contains explicit evaluator predicates.
- 12番: MEDIUM feature gates can be mapped from explicit thresholds, but final signal remains blocked until arbitration.

## 9. Things not implemented in this step

- Live evaluator execution.
- CoreA/CoreB rule approximation.
- Historical ledger `entry_time` based signaling.
- Discord actual notification.
- MT5 order execution.
- AI review/API.
- Live hook integration.
- NO_SIGNAL notification.

## 10. Next step after this audit

Step 13 may connect a live evaluator only after CoreA/CoreB mapping JSON has no blocking `UNMAPPED_CONDITION`. Until then, live signal generation must remain blocked.
