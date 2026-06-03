# GOLD V2 CoreA / CoreB / MEDIUM signal conditions - no-approx implementation guard

Date: 2026-06-03  
Repo: `knitanr-a11y/xauusd-signal-lab`

この文書は、CoreA / CoreB / MEDIUM の live シグナル条件を近似実装しないためのガードです。次チャットでは必ず以下の引き継ぎ文書と一緒に読んでください。

```text
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_COREA_COREB_MEDIUM_LIVE_RULES_20260603.md
docs/gold_v2/GOLD_V2_COREA_COREB_MEDIUM_SIGNAL_CONDITIONS_NO_APPROX_GUARD_20260603.md
```

---

## 0. 絶対ルール

1. CoreA / CoreB / MEDIUM を履歴 ledger の `entry_time` 一致だけで live シグナル化しない。
2. CoreA / CoreB をOHLCパターンからそれっぽく再検出しない。
3. 旧GOLD / DISC8 のロジックを source of truth に戻さない。
4. 条件が完全に mapping できない場合は `UNMAPPED_CONDITION` として停止する。
5. frozen JSON や source hash が無い、または一致しない場合は `RULE_SOURCE_MISSING` / `RULE_SOURCE_HASH_MISMATCH` として停止する。
6. evaluator が未完成の場合は `RULE_SOURCE_PRESENT_BUT_EVALUATOR_NOT_IMPLEMENTED` / `EVALUATOR_MAPPING_INCOMPLETE` として停止する。
7. NO_SIGNAL では Discord 通知しない。`notification_preview_text` は空にする。
8. Discord送信・MT5発注・AI API・live hook は明示許可までOFF。

---

## 1. 現在の frozen source JSON

11番で生成する想定のファイル:

```text
configs/gold_v2/frozen_coreA_fold4_ABC_CAP5_rules_20260603.json
configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json
configs/gold_v2/frozen_medium_rules_20260603.json
```

これらは **source manifest** であり、完全な evaluator mapping ではありません。`FROZEN_RULE_SOURCE_READY` は「sourceファイル・hash・schema・採用条件の固定ができた」という意味で、live判定が完成したという意味ではありません。

---

## 2. CoreA 条件ガード

### 2.1 採用名

```text
component: HIGH_A_CoreA_fold4_ABC_CAP5
priority: HIGH_A
name: CoreA_fold4_ABC_CAP5
source policy: FROZEN_GOLD_V2_COREA_FOLD4_ABC_CAP5_20260603
```

### 2.2 採用コンセプト

```text
CoreA = fold4_rules + ABC entry gate + A_CAP5_BC_CAP3 sizing
```

固定内容:

```text
ruleset = fold4_rules
entry_gate = ABC
A sizing = CAP5
B sizing = CAP3
C sizing = CAP3
lot_multiplier_candidate = 1.0
```

### 2.3 ABC gate の概要

```text
A:
  10-day lookback
  tail_hard
  top5
  all consensus
  stack allowed only KEEP
  otherwise REJECT

B:
  CoreA rejected
  AND regime == MID_MIXED
  AND trend_eff96 >= 0.633155
  AND RR >= 1.5

C:
  range96 >= 100.43
  AND range96 <= 117.86
```

### 2.4 CoreAで禁止すること

```text
- abc_stack_cap_*_cluster_ledger.csv の top_entry_time を未来のliveシグナル源にすること
- cluster_id の履歴検索だけでliveシグナル化すること
- fold4_rules を最終勝ちクラスタから推測すること
- ABCを range96 / trend_eff96 だけで簡易再現すること
- TP150_SL150 をCoreA全体の固定TP/SLだとみなすこと
```

### 2.5 CoreAの停止状態

```text
RULE_SOURCE_MISSING
RULE_SOURCE_HASH_MISMATCH
RULE_SOURCE_PRESENT_BUT_EVALUATOR_NOT_IMPLEMENTED
EVALUATOR_MAPPING_INCOMPLETE
UNMAPPED_CONDITION
```

上記の場合は必ず:

```text
signal_eligible = false
```

---

## 3. CoreB 条件ガード

### 3.1 採用名

```text
component: HIGH_B_CoreB_RR125_BUY_CONFLUENCE
priority: HIGH_B
name: RR125_BUY_CONFLUENCE
source policy: FROZEN_GOLD_V2_COREB_RR125_BUY_CONFLUENCE_20260603
```

### 3.2 採用コンセプト

```text
CoreB = RR1.0-derived BUY rules re-evaluated with TP = 1.25 * SL
```

固定内容:

```text
direction = BUY only
source rules = BUY rules originally selected at RR1.0
entry conditions = original RR1.0 BUY rule entry conditions
SL width = original source rule SL width
TP width = 1.25 * SL width
same_count >= 15
sizing = CAP3
lot_multiplier_candidate = 1.0
```

### 3.3 CoreB confluence

CoreA BUY と CoreB BUY が同じ `entry_time` の場合:

```text
priority = HIGH_CONFLUENCE
initial extra CoreB exposure = 0.5
effective lot = 1.5 equivalent
```

CoreA SELL と CoreB BUY が同じ `entry_time` の場合:

```text
CoreA has priority
CoreB is skipped
```

### 3.4 CoreBで禁止すること

```text
- rr125_top_ledgers.csv の entry_time を未来のliveシグナル源にすること
- historical same_count をlive計算済み条件として扱うこと
- 現在足が上昇っぽいだけでBUYを出すこと
- RR1.0 source rules を candidate_id / origin_id から推測すること
- CoreBでSELLを許可すること
```

### 3.5 CoreBの停止状態

```text
RULE_SOURCE_MISSING
RULE_SOURCE_HASH_MISMATCH
RULE_SOURCE_PRESENT_BUT_EVALUATOR_NOT_IMPLEMENTED
EVALUATOR_MAPPING_INCOMPLETE
UNMAPPED_CONDITION
UNMAPPED_SAME_COUNT_SOURCE
```

上記の場合は必ず:

```text
signal_eligible = false
```

---

## 4. MEDIUM 条件ガード

### 4.1 採用名

```text
component: MEDIUM_REFINED_FEATURE_GATES
priority: MEDIUM
source policy: FROZEN_GOLD_V2_MEDIUM_REFINED_RULES_20260603
lot_multiplier_candidate = 0.5
```

### 4.2 優先順位

```text
HIGH_CONFLUENCE > HIGH_A > HIGH_B > MEDIUM
```

MEDIUMは、CoreA/CoreBのarbitration完了前に最終シグナルになってはいけない。

### 4.3 RANGE96_REFINED

```text
range96 >= 129.6835
AND trend_eff96 <= 0.355591
AND top_direction == SELL
CAP3
lot_multiplier_candidate = 0.5
```

注意:

```text
top_direction == SELL は最新M15ローソク色ではない。
source rule mappingから明示的に取れない場合は UNMAPPED_CONDITION で停止する。
```

### 4.4 VOL_TRMEAN32_REFINED

```text
tr_mean_32 >= 10.867578
AND ret96 <= -2.725
AND range96 >= 176.453
CAP3
lot_multiplier_candidate = 0.5
```

注意:

```text
方向がPROBEのままなら、BUY/SELLを推測してはいけない。
source rule mappingから方向が確定できない場合は UNMAPPED_DIRECTION で停止する。
```

### 4.5 TIER2_HVT

```text
trend_eff96 <= 0.4
AND ret96 <= -25.0
AND tr_mean_32 >= 10.867578
CAP3
lot_multiplier_candidate = 0.5
```

注意:

```text
TIER2_HVT は Tier2 static plus HIGH_VOL_TREND として扱われていた。
Tier2 static の追加条件が明示mappingできない場合は UNMAPPED_TIER2_STATIC で停止する。
```

### 4.6 MEDIUMで禁止すること

```text
- 特徴量ヒットだけで最終シグナル化すること
- CoreA/CoreB arbitrationを省略すること
- 最新M15足の陽線/陰線から方向を推測すること
- CoreA rejected を、CoreA evaluator未実行なのにtrue扱いすること
- FEATURE_PROBE_ONLY をシグナル扱いすること
```

### 4.7 MEDIUMの停止状態

```text
FEATURE_GATE_ONLY
BLOCKED_BY_MISSING_HIGH_ARBITRATION
UNMAPPED_CONDITION
UNMAPPED_DIRECTION
UNMAPPED_TIER2_STATIC
```

上記の場合は必ず:

```text
signal_eligible = false
```

---

## 5. NO_SIGNAL / Discord policy

NO_SIGNALはDiscordに通知しない。

必須出力:

```json
{
  "final_signal_status": "NO_SIGNAL",
  "notification_should_send": false,
  "notification_preview_text": "",
  "no_signal_discord_policy": "DO_NOT_NOTIFY_ON_NO_SIGNAL"
}
```

監査レポートにはNO_SIGNAL理由を残してよい。Discord previewは空にする。

---

## 6. 次の実装順

```text
12_MAP_FROZEN_RULES_TO_LIVE_EVALUATOR_AUDIT_ONLY
  - frozen manifestを明示condition objectへ落とす
  - mapped/unmappedを出す
  - signalはまだ出さない

13_EVALUATE_LIVE_RULES_WITH_MAPPING_AUDIT_ONLY
  - mapped条件だけ評価
  - unmappedがあるcomponentはsignal_eligible=false
  - arbitration実行
  - SIGNAL or NO_SIGNAL
  - NO_SIGNALなら通知文面空

14_PREFLIGHT_LIVE_EVALUATOR_AUDIT_ONLY
  - HTF確定済み制約
  - source hash一致
  - no external actions
  - NO_SIGNAL通知禁止
```

---

## 7. future evaluator 必須出力

各component evaluatorは必ず出す:

```text
component
status
signal_eligible
mapped_conditions
unmapped_conditions
source_files
source_hash_check
feature_values_used
blocked_reason
```

最終packetは必ず出す:

```text
final_signal_status
selected_component
selected_direction
selected_lot_multiplier
notification_should_send
notification_preview_text
no_signal_discord_policy
external_actions.discord_send_allowed
external_actions.mt5_order_allowed
external_actions.ai_api_allowed
external_actions.live_hook_allowed
```

---

## 8. 結論

CoreA/CoreB/MEDIUMは、完全なfrozen-rule mappingができるまでlive signalにしてはいけない。

それまでは:

```text
CoreA/CoreB:
  RULE_SOURCE_PRESENT_BUT_EVALUATOR_NOT_IMPLEMENTED
  or EVALUATOR_MAPPING_INCOMPLETE

MEDIUM:
  FEATURE_GATE_ONLY
  or BLOCKED_BY_MISSING_HIGH_ARBITRATION

final_signal_status:
  NO_SIGNAL unless fully mapped component is eligible

NO_SIGNAL:
  notification_preview_text = ""
```
