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

確定済みのCoreB採用条件:

```text
direction = BUY only
source_policy = RR125_from_RR1_rules
source rules = BUY rules originally selected at RR1.0
SL width = original source rule SL width
TP width = 1.25 * SL width
same_count >= 15
sizing = CAP3
lot_multiplier_candidate = 1.0
```

### 3.3 CoreBでまだ未凍結の条件

ここが重要。現時点の文書・frozen JSONに書けているのは、CoreBの**採用後フィルタ**と**sourceファイルのmanifest**までです。CoreBの元になった **RR1.0 BUY source rule の個別エントリー条件式そのもの** は、まだlive evaluatorへ渡せる形で凍結されていません。

未凍結のもの:

```text
- RR1.0 BUY source ruleごとの具体的なentry condition式
- source_rule_count の内訳となる各source ruleの条件式
- same_countをliveで再計算するための母集団ルール定義
- base_condition / added_filter_text を実行可能condition objectへ変換したmapping
- candidate_id / origin_idごとの明示的条件表
```

CoreB frozen JSONに存在する `rr125_top_ledgers.csv` と `rr125_raw_signal_ledger.csv` はsource lineageとして重要だが、それだけではlive条件式としては不十分。特に `entry_time` やhistorical `same_count` をそのまま使ってlive BUYを出してはいけない。

したがって、次チャットでCoreBを実装する場合、まず以下を作る必要がある:

```text
12A_FREEZE_COREB_SOURCE_RULE_CONDITIONS_AUDIT_ONLY
  input:
    rr125_raw_signal_ledger.csv
    rr125_top_ledgers.csv
  output:
    configs/gold_v2/frozen_coreB_rr125_source_rule_conditions_20260603.json
  required extracted columns:
    policy
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
    train_score
  required validation:
    direction must be BUY
    policy must include RR125_from_RR1_rules
    source RR1.0 base conditions must be non-empty
    unique source rule definitions must be listed explicitly
```

`base_condition` / `added_filter_text` が自然文または未解析文字列のままなら、CoreB evaluatorはまだ実装不可。必ず:

```text
CoreB status = UNMAPPED_SOURCE_RULE_CONDITIONS
signal_eligible = false
```

### 3.4 CoreB confluence

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

### 3.5 CoreBで禁止すること

```text
- rr125_top_ledgers.csv の entry_time を未来のliveシグナル源にすること
- rr125_raw_signal_ledger.csv の historical entry_time をliveシグナル源にすること
- historical same_count をlive計算済み条件として扱うこと
- 現在足が上昇っぽいだけでBUYを出すこと
- RR1.0 source rules を candidate_id / origin_id から推測すること
- base_condition / added_filter_text を読まずにCoreBを作ること
- base_condition / added_filter_text を読んでも、実行可能condition objectへ落とさずにシグナル化すること
- CoreBでSELLを許可すること
```

### 3.6 CoreBの停止状態

```text
RULE_SOURCE_MISSING
RULE_SOURCE_HASH_MISMATCH
RULE_SOURCE_PRESENT_BUT_EVALUATOR_NOT_IMPLEMENTED
EVALUATOR_MAPPING_INCOMPLETE
UNMAPPED_CONDITION
UNMAPPED_SAME_COUNT_SOURCE
UNMAPPED_SOURCE_RULE_CONDITIONS
UNPARSED_BASE_CONDITION
UNPARSED_ADDED_FILTER_TEXT
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
12A_FREEZE_COREB_SOURCE_RULE_CONDITIONS_AUDIT_ONLY
  - rr125_raw_signal_ledger.csv からCoreB元ルール条件を抽出
  - base_condition / added_filter_text を明示的に一覧化
  - 解析不能なら UNPARSED_* として止める

12_MAP_FROZEN_RULES_TO_LIVE_EVALUATOR_AUDIT_ONLY
  - frozen manifestを明示condition objectへ落とす
  - CoreBは12Aのsource rule conditionsなしでは実装禁止
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

CoreB evaluatorは追加で必ず出す:

```text
source_rule_condition_count
source_rule_conditions_mapped_count
source_rule_conditions_unmapped_count
same_count_live_recalculated
same_count_source_rule_ids
base_condition_parse_status
added_filter_text_parse_status
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

特にCoreBは、現在の文書だけでは元RR1.0 BUYルールの個別entry条件がまだ不足している。次に必ず `12A_FREEZE_COREB_SOURCE_RULE_CONDITIONS_AUDIT_ONLY` を作り、`base_condition` / `added_filter_text` をsource of truthとして凍結すること。

それまでは:

```text
CoreA/CoreB:
  RULE_SOURCE_PRESENT_BUT_EVALUATOR_NOT_IMPLEMENTED
  or EVALUATOR_MAPPING_INCOMPLETE
  or UNMAPPED_SOURCE_RULE_CONDITIONS

MEDIUM:
  FEATURE_GATE_ONLY
  or BLOCKED_BY_MISSING_HIGH_ARBITRATION

final_signal_status:
  NO_SIGNAL unless fully mapped component is eligible

NO_SIGNAL:
  notification_preview_text = ""
```
