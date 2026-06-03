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

## 8. BAT仕様

### 8.1 11_FREEZE_RULE_SOURCES_AUDIT_ONLY.bat

BAT:

```text
scripts\gold_v2_runtime\bat\11_FREEZE_RULE_SOURCES_AUDIT_ONLY.bat
```

実行内容:

```text
python scripts\gold_v2_runtime\freeze_gold_v2_rule_sources_audit_only.py %*
```

役割:

- ユーザー環境の探索済みCSVを読み、frozen rule-source manifest JSONを生成する。
- これはlive evaluatorではない。
- 近似再実装はしない。
- Discord通知、MT5発注、AI API、live hookは呼ばない。

主な生成先:

```text
configs/gold_v2/
Files/FX_OUTPUTS/gold_v2_frozen_rule_sources_audit_only/
```

生成される必要ファイル:

```text
configs/gold_v2/frozen_coreA_fold4_ABC_CAP5_rules_20260603.json
configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json
configs/gold_v2/frozen_medium_rules_20260603.json
Files/FX_OUTPUTS/gold_v2_frozen_rule_sources_audit_only/frozen_coreA_fold4_ABC_CAP5_rules_20260603.json
Files/FX_OUTPUTS/gold_v2_frozen_rule_sources_audit_only/frozen_coreB_rr125_buy_confluence_rules_20260603.json
Files/FX_OUTPUTS/gold_v2_frozen_rule_sources_audit_only/frozen_medium_rules_20260603.json
Files/FX_OUTPUTS/gold_v2_frozen_rule_sources_audit_only/gold_v2_frozen_rule_sources_summary.json
Files/FX_OUTPUTS/gold_v2_frozen_rule_sources_audit_only/GOLD_V2_FROZEN_RULE_SOURCES_AUDIT_ONLY_REPORT.md
```

成功確認:

```text
core_status=FROZEN_RULE_SOURCE_READY
coreb_status=FROZEN_RULE_SOURCE_READY
medium_status=FROZEN_RULE_SOURCE_READY
all_required_ready=True
```

停止条件:

- required CSVが無い。
- CSVが読めない。
- CoreA/CoreB/MEDIUMのいずれかが `FROZEN_RULE_SOURCE_READY` にならない。

### 8.2 10_EVALUATE_LIVE_RULES_AUDIT_ONLY.bat

BAT:

```text
scripts\gold_v2_runtime\bat\10_EVALUATE_LIVE_RULES_AUDIT_ONLY.bat
```

実行内容:

```text
python scripts\gold_v2_runtime\evaluate_gold_v2_live_rules_audit_only.py %*
```

役割:

- 最新M15特徴量を作成し、live rule evaluation audit gateを実行する。
- CoreA/CoreB frozen JSONが無ければ `RULE_SOURCE_MISSING`。
- CoreA/CoreB frozen JSONがあれば、現段階では `RULE_SOURCE_PRESENT_BUT_EVALUATOR_NOT_IMPLEMENTED`。
- MEDIUM特徴条件は評価するが、CoreA/CoreB arbitration未接続のため最終signalにはしない。
- NO_SIGNAL時は `notification_preview_text=""`、`notification_should_send=false`。
- Discord通知、MT5発注、AI API、live hookは呼ばない。

主な生成先:

```text
Files/FX_OUTPUTS/gold_v2_live_rule_evaluation_audit_only/
```

生成される必要ファイル:

```text
Files/FX_OUTPUTS/gold_v2_live_rule_evaluation_audit_only/gold_v2_live_rule_evaluation_packet.json
Files/FX_OUTPUTS/gold_v2_live_rule_evaluation_audit_only/GOLD_V2_LIVE_RULE_EVALUATION_AUDIT_ONLY_REPORT.md
Files/FX_OUTPUTS/gold_v2_live_rule_evaluation_audit_only/gold_v2_live_rule_core_eval.csv
Files/FX_OUTPUTS/gold_v2_live_rule_evaluation_audit_only/gold_v2_live_rule_medium_eval.csv
Files/FX_OUTPUTS/gold_v2_live_rule_evaluation_audit_only/gold_v2_live_rule_notification_preview.txt
```

成功確認:

```text
core_evaluators[].status=RULE_SOURCE_PRESENT_BUT_EVALUATOR_NOT_IMPLEMENTED
final_signal_status=NO_SIGNAL または SIGNAL候補なし
notification_should_send=false
notification_preview_text=""  # NO_SIGNAL時
external_actions.discord_send_allowed=false
external_actions.mt5_order_allowed=false
external_actions.ai_api_allowed=false
external_actions.live_hook_allowed=false
```

停止条件:

- M15 CSVが無い。
- eval_timeがM15 CSVに存在しない。
- candle列が不足している。
- frozen JSON生成後なのにCoreA/CoreBが `RULE_SOURCE_MISSING` のまま。

### 8.3 12_MAP_FROZEN_RULES_TO_LIVE_EVALUATOR_AUDIT_ONLY.bat

BAT:

```text
scripts\gold_v2_runtime\bat\12_MAP_FROZEN_RULES_TO_LIVE_EVALUATOR_AUDIT_ONLY.bat
```

実行内容:

```text
python scripts\gold_v2_runtime\map_gold_v2_frozen_rules_to_live_evaluator_audit_only.py %*
```

役割:

- 11番で生成された frozen CoreA/CoreB/MEDIUM JSONを読む。
- policy JSONの安全設定を確認する。
- manifest source fileのfingerprintを監査情報として保持する。
- CoreA/CoreBについて、明示的なlive evaluator条件が無ければ `UNMAPPED_CONDITION` として止める。
- MEDIUMについて、`definition.rules[].conditions` の `_min/_max/_eq` 条件だけをfeature-gate mappingする。
- MEDIUMはfeature-gate mappingできても、CoreA/CoreB arbitration未接続のため `final_signal_allowed=false` のままにする。
- 近似再実装、entry_time一致signal化、Discord通知、MT5発注、AI API、live hookは行わない。

主な生成先:

```text
configs/gold_v2/
Files/FX_OUTPUTS/gold_v2_live_evaluator_mapping_audit_only/
```

生成される必要ファイル:

```text
configs/gold_v2/live_evaluator_mapping_coreA_20260603.json
configs/gold_v2/live_evaluator_mapping_coreB_20260603.json
configs/gold_v2/live_evaluator_mapping_medium_20260603.json
Files/FX_OUTPUTS/gold_v2_live_evaluator_mapping_audit_only/live_evaluator_mapping_coreA_20260603.json
Files/FX_OUTPUTS/gold_v2_live_evaluator_mapping_audit_only/live_evaluator_mapping_coreB_20260603.json
Files/FX_OUTPUTS/gold_v2_live_evaluator_mapping_audit_only/live_evaluator_mapping_medium_20260603.json
Files/FX_OUTPUTS/gold_v2_live_evaluator_mapping_audit_only/gold_v2_live_evaluator_mapping_summary.json
Files/FX_OUTPUTS/gold_v2_live_evaluator_mapping_audit_only/gold_v2_live_evaluator_mapping_status.csv
Files/FX_OUTPUTS/gold_v2_live_evaluator_mapping_audit_only/gold_v2_live_evaluator_mapping_audit_checks.csv
Files/FX_OUTPUTS/gold_v2_live_evaluator_mapping_audit_only/gold_v2_live_evaluator_mapping_unmapped_conditions.csv
Files/FX_OUTPUTS/gold_v2_live_evaluator_mapping_audit_only/GOLD_V2_LIVE_EVALUATOR_MAPPING_AUDIT_ONLY_REPORT.md
```

終了コード:

| Code | 意味 | 扱い |
|---:|---|---|
| 0 | blocking `UNMAPPED_CONDITION` なし、または `--allow-unmapped-exit-zero` 指定時 | audit完了。ただしlive接続は別工程 |
| 2 | blocking `UNMAPPED_CONDITION` あり | 正常な安全停止。live evaluatorへ接続してはいけない |
| その他 | JSON欠落、policy safety失敗、読み込み失敗など | 異常停止 |

成功確認:

```text
gold_v2_live_evaluator_mapping_summary.json
  status=BLOCKED_UNMAPPED_CONDITION  # 現状の期待値
  external_actions.discord_send_allowed=false
  external_actions.mt5_order_allowed=false
  external_actions.ai_api_allowed=false
  external_actions.live_hook_allowed=false
  no_signal_discord_policy=DO_NOT_NOTIFY_ON_NO_SIGNAL

live_evaluator_mapping_coreA_20260603.json
  status=MAPPING_BLOCKED_UNMAPPED_CONDITION
  final_signal_allowed=false
  historical_entry_time_match_allowed=false

live_evaluator_mapping_coreB_20260603.json
  status=MAPPING_BLOCKED_UNMAPPED_CONDITION
  final_signal_allowed=false
  historical_entry_time_match_allowed=false

live_evaluator_mapping_medium_20260603.json
  status=MAPPED_FEATURE_GATES_ONLY_BLOCKED_FOR_FINAL_SIGNAL または MAPPING_BLOCKED_UNMAPPED_CONDITION
  final_signal_allowed=false
```

停止条件:

- frozen JSONが存在しない。
- frozen JSONがparseできない。
- frozen manifest statusが `FROZEN_RULE_SOURCE_READY` ではない。
- policy safetyがaudit-only false条件を満たさない。
- CoreA/CoreBの明示live条件が足りない。
- MEDIUM条件に対応外suffixがある。
- blocking `UNMAPPED_CONDITION` がある。

## 9. Execution order and required generated files

Run in this order:

```text
scripts\gold_v2_runtime\bat\11_FREEZE_RULE_SOURCES_AUDIT_ONLY.bat
scripts\gold_v2_runtime\bat\10_EVALUATE_LIVE_RULES_AUDIT_ONLY.bat
scripts\gold_v2_runtime\bat\12_MAP_FROZEN_RULES_TO_LIVE_EVALUATOR_AUDIT_ONLY.bat
```

### 9.1 After running 11

Check this folder:

```text
Files/FX_OUTPUTS/gold_v2_frozen_rule_sources_audit_only/
```

Required files:

```text
GOLD_V2_FROZEN_RULE_SOURCES_AUDIT_ONLY_REPORT.md
gold_v2_frozen_rule_sources_summary.json
frozen_coreA_fold4_ABC_CAP5_rules_20260603.json
frozen_coreB_rr125_buy_confluence_rules_20260603.json
frozen_medium_rules_20260603.json
```

Also check these config files:

```text
configs/gold_v2/frozen_coreA_fold4_ABC_CAP5_rules_20260603.json
configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json
configs/gold_v2/frozen_medium_rules_20260603.json
```

Expected status:

```text
core_status=FROZEN_RULE_SOURCE_READY
coreb_status=FROZEN_RULE_SOURCE_READY
medium_status=FROZEN_RULE_SOURCE_READY
```

Do not continue if any frozen source is missing or incomplete.

### 9.2 After running 10

Check this folder:

```text
Files/FX_OUTPUTS/gold_v2_live_rule_evaluation_audit_only/
```

Required files:

```text
gold_v2_live_rule_evaluation_packet.json
GOLD_V2_LIVE_RULE_EVALUATION_AUDIT_ONLY_REPORT.md
gold_v2_live_rule_core_eval.csv
gold_v2_live_rule_medium_eval.csv
gold_v2_live_rule_notification_preview.txt
```

Expected status:

```text
CoreA/CoreB:
  RULE_SOURCE_PRESENT_BUT_EVALUATOR_NOT_IMPLEMENTED

NO_SIGNALの場合:
  notification_preview_text=""
  notification_should_send=false
```

Do not continue if CoreA/CoreB are still `RULE_SOURCE_MISSING` after 11 generated the frozen JSON.

### 9.3 After running 12

Check this folder:

```text
Files/FX_OUTPUTS/gold_v2_live_evaluator_mapping_audit_only/
```

Required files:

```text
GOLD_V2_LIVE_EVALUATOR_MAPPING_AUDIT_ONLY_REPORT.md
gold_v2_live_evaluator_mapping_summary.json
gold_v2_live_evaluator_mapping_status.csv
gold_v2_live_evaluator_mapping_audit_checks.csv
gold_v2_live_evaluator_mapping_unmapped_conditions.csv
live_evaluator_mapping_coreA_20260603.json
live_evaluator_mapping_coreB_20260603.json
live_evaluator_mapping_medium_20260603.json
```

Also check these config files:

```text
configs/gold_v2/live_evaluator_mapping_coreA_20260603.json
configs/gold_v2/live_evaluator_mapping_coreB_20260603.json
configs/gold_v2/live_evaluator_mapping_medium_20260603.json
```

Expected current result:

```text
CoreA:
  status=MAPPING_BLOCKED_UNMAPPED_CONDITION

CoreB:
  status=MAPPING_BLOCKED_UNMAPPED_CONDITION

MEDIUM:
  status=MAPPED_FEATURE_GATES_ONLY_BLOCKED_FOR_FINAL_SIGNAL
  or status=MAPPING_BLOCKED_UNMAPPED_CONDITION if frozen MEDIUM conditions are incomplete

Summary:
  status=BLOCKED_UNMAPPED_CONDITION
  live_evaluator_connection_allowed=false
```

This is a safe stop, not a failure of the guard. It means CoreA/CoreB still do not have enough explicit frozen predicates for a live evaluator.

Do not run or implement step 13 as a signal-producing evaluator until the mapping JSON has no blocking `UNMAPPED_CONDITION`.

## 10. Things not implemented in this step

- Live evaluator execution.
- CoreA/CoreB rule approximation.
- Historical ledger `entry_time` based signaling.
- Discord actual notification.
- MT5 order execution.
- AI review/API.
- Live hook integration.
- NO_SIGNAL notification.

## 11. Next step after this audit

Step 13 may connect a live evaluator only after CoreA/CoreB mapping JSON has no blocking `UNMAPPED_CONDITION`. Until then, live signal generation must remain blocked.
