# NEXT CHAT HANDOFF — GOLD V2 OHLC live evaluator reproduction

作成日: 2026-06-05  
repo: `knitanr-a11y/xauusd-signal-lab`  
主題: **OHLCからlive evaluatorとしてCoreA / CoreB / MEDIUMを再計算し、既存SOT/バックテスト結果と一致させる再現監査**  
最終完成形: **Discord通知 + MT5 guarded autotrading**  
直近の作業位置: **13D完了。次は13D-2。ただし最終目標はOHLC→feature→rule→candidateの再現。**

---

## 0. このハンドオフで明確にすること

前回までに、source ledger / final SOT を使った historical replay はかなり整理できている。

しかし、今から進める本題はこれ。

```text
OHLCからlive evaluatorとして再計算して、
同じCoreA / CoreB / MEDIUMの結果をどこまで再現できるかを確認する。
```

つまり、単に `final SOT CSV` や `source ledger CSV` を読むだけでは不十分。  
今後は以下を段階的に再現する。

```text
OHLC
  -> feature計算
  -> asof timing
  -> rule判定
  -> component候補
  -> CoreA/CoreB/MEDIUM arbitration
  -> dry-run candidate
  -> Discord通知preview
  -> MT5 order preview
  -> guarded Discord通知 + MT5自動売買
```

---

## 1. 絶対ルール

### 1.1 近似再実装は禁止

以下は禁止。

```text
探索済み条件に似せてOHLCから新しく条件を作る
sourceにない条件を勝手に作る
same_count / cluster_id を固定windowなどで代用する
TIER2_HVT mismatchを無視してmanifestを通す
```

### 1.2 Source of truth

過去検証のsource of truthは以下。

```text
gold_v2_final_portfolio_2025_2026_sot_ledger.csv
CoreA source selected rows
rr125_top_ledgers.csv
rr125_raw_signal_ledger.csv
coreb_refined_rule_ledgers.csv
frozen_coreA / frozen_coreB / frozen_medium config
13A〜13Dのaudit出力
```

OHLCは **新規探索用ではなく、既存source条件をlive evaluatorとして再現できるか確認するため** に使う。

### 1.3 外部アクション禁止

まだ以下は禁止。

```text
Discord実送信禁止
MT5発注禁止
AI API禁止
live hook禁止
```

---

## 2. 既存のhistorical SOT結果

Final SOT:

```text
total = 529
2025 = 346
2026 = 183
```

source内訳:

```text
CORE_A_CORE_B_CONFLUENCE       8
CORE_A_ONLY                  317
CORE_B_ONLY                  117
MEDIUM_RANGE96_REFINED        51
MEDIUM_TIER2_HVT              13
MEDIUM_VOL_TRMEAN32_REFINED   23
```

component historical rows:

```text
CoreA historical = 325
CoreB historical = 125
MEDIUM final SOT = 87
```

MEDIUM 13D replay:

```text
MEDIUM source rows = 118
MEDIUM final SOT rows = 87
internal priority dropped rows = 31
arbitration replay matches final SOT = true
```

---

## 3. 再現レベルの定義

今後の「再現」は段階を分けて扱う。

### Level 1 — Historical SOT replay

```text
source ledger / final SOTを読むだけで同じバックテスト結果を再集計できる
```

状態:

```text
ほぼ完了済み
```

### Level 2 — Source feature snapshot parity

```text
source entry_timeの行で、source ledgerにあるfeature値と再計算feature値が一致する
```

目的:

```text
OHLCから作るfeatureがsourceの意味と一致するか確認する
```

### Level 3 — Rule replay from feature snapshot

```text
feature snapshotからCoreA/CoreB/MEDIUMのrule判定を行い、source ledgerの採用行と一致する
```

### Level 4 — OHLC to feature to rule end-to-end replay

```text
OHLCだけを入力としてfeatureを作り、ruleを判定し、historical SOTに近い/同一のcandidate ledgerを出す
```

これが今から本格的に目指す再現。

### Level 5 — Runtime dry-run evaluator

```text
最新OHLCからlive candidateを出す
Discord/MT5はまだOFF
```

### Level 6 — Discord + MT5 guarded autotrading

```text
Discordに実通知し、MT5でguarded auto orderを出し、position/close/勝敗をledger化する
```

これが最終完成形。

---

## 4. Component別の現状と再現方針

## 4.1 CoreA

### Historical status

```text
CoreA historical SOT = ready
CoreA rows = 325
2025 count = 200
2026 count = 125
```

### Live reproduction blockers

```text
A gate未凍結
tail_hard / top5 / all-consensus / stack KEEP の実行可能条件が未確定
B_rr15 / C_fixed は比較的明確だが、CoreA_REJECT順序とfeature/asof parityが必要
```

### 今後の再現方針

CoreAは一気に全部再現しない。順序は以下。

```text
1. B_rr15 と C_fixed のfeature/asof parityを確認
2. A gateのsource条件を探す/凍結する
3. A gateが見つからない場合、CoreA full liveはblocked
4. B/Cだけ部分live候補にできるか別枠で判定
```

CoreAで絶対にしてはいけないこと:

```text
is_A flag だけでA gateをlive実装する
A gateを雰囲気で近似する
```

---

## 4.2 CoreB

### Historical status

```text
CoreB historical SOT = allowed
CoreB rows = 125
2025 count = 104
2026 count = 21
```

### Live reproduction blockers

13C-5で確定。

```text
true_original_clustering_candidate_files = 0
original same_count / cluster_id algorithm not found
row-level cluster membership ledger missing
```

13C-2/13C-3で失敗した代替案:

```text
raw exact entry_time count        -> 不一致
interval cover count             -> 不一致
connected component count         -> 不一致
fixed entry window                -> 不一致
single feature row rule hit count -> 不一致
```

### 今後の再現方針

CoreBのOHLC live再現は、現時点では **止める**。

再開条件:

```text
original clustering algorithm が見つかる
または row-level cluster membership ledger が見つかる
または source same_count をlive-computableに変換できる正式根拠が見つかる
```

それまでは:

```text
CoreB historical SOT only
CoreB live evaluator blocked
Approximate same_count forbidden
```

---

## 4.3 MEDIUM

### Historical status

13Dで確認済み。

```text
MEDIUM source rows = 118
MEDIUM final SOT rows = 87
arbitration replay = matches final SOT
```

内訳:

```text
RANGE96_REFINED:
  source_rows = 51
  final_rows = 51
  manifest_match_rows = 51 / 51

VOL_TRMEAN32_REFINED:
  source_rows = 36
  final_rows = 23
  internal_priority_dropped_rows = 13
  manifest_match_rows = 36 / 36

TIER2_HVT:
  source_rows = 31
  final_rows = 13
  manifest_match_rows = 19 / 31
  manifest_mismatch_rows = 12 / 31
  final_sot_manifest_match_rows = 2 / 13
  final_sot_manifest_mismatch_rows = 11 / 13
```

### Live reproduction blockers

```text
TIER2_HVT manifest mismatch
feature/asof parity未証明
HIGH arbitration dependency
```

### 今後の再現方針

MEDIUMは最もlive再現に近い。

順序:

```text
13D2:
  TIER2_HVT source definition reconciliation

13D3:
  TIER2_HVTを単一修正 / variant split / historical-only block のどれにするか決定

13E:
  RANGE96_REFINED / VOL_TRMEAN32_REFINED / TIER2候補のfeature/asof parity

13F:
  live eligibility matrix
```

---

## 5. 次にやること

次の工程はこれ。

```text
13D2_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY
```

目的:

```text
TIER2_HVT source 31件をmanifest match/mismatchに分解
final SOT TIER2 13件のうち11件がなぜmanifest外なのか特定
TIER2_HVTが単一条件で直せるのか、複数variantが必要なのか、historical-onlyなのか判定
```

13D2はOHLC再探索ではない。  
13D出力とsource ledgerを見て、TIER2_HVTのsource定義を再整理する。

---

## 6. 13D2の入力

優先入力:

```text
Files\FX_OUTPUTS\gold_v2_13d_medium_feature_arbitration_audit_only\gold_v2_13d_medium_source_rows_with_manifest_match.csv
Files\FX_OUTPUTS\gold_v2_13d_medium_feature_arbitration_audit_only\gold_v2_13d_medium_recomputed_final_rows.csv
Files\FX_OUTPUTS\gold_v2_13d_medium_feature_arbitration_audit_only\gold_v2_13d_medium_final_sot_rule_summary.csv
Files\FX_OUTPUTS\gold_v2_13d_medium_feature_arbitration_audit_only\gold_v2_13d_medium_rule_manifest_inventory.csv
Files\FX_OUTPUTS\gold_v2_13d_medium_feature_arbitration_audit_only\gold_v2_13d_medium_rule_manifest_coverage.csv
```

参照:

```text
configs\gold_v2\frozen_medium_rules_20260603.json
Files\FX_OUTPUTS\gold_v2_final_portfolio_sot_freeze_audit_only\gold_v2_final_portfolio_2025_2026_sot_ledger.csv
Files\FX_OUTPUTS\gold_v2_coreb_refined_probe_outputs\coreb_refined_rule_ledgers.csv
```

---

## 7. 13D2の期待件数

必ず以下を満たすこと。

```text
TIER2_HVT source rows = 31
TIER2_HVT final SOT rows = 13
TIER2_HVT source manifest match rows = 19
TIER2_HVT source manifest mismatch rows = 12
TIER2_HVT final manifest match rows = 2
TIER2_HVT final manifest mismatch rows = 11
```

これが再現しない場合は停止。

---

## 8. 13D2の出力予定

フォルダ:

```text
Files\FX_OUTPUTS\gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only
```

本体:

```text
scripts\gold_v2_runtime\audit_gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only.py
```

BAT:

```text
scripts\gold_v2_runtime\bat\13D2_AUDIT_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY.bat
```

最初に見るファイル:

```text
GOLD_V2_13D2_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY_REPORT.md
gold_v2_13d2_medium_tier2_hvt_reconciliation_summary.json
```

補助ファイル:

```text
gold_v2_13d2_input_audit.csv
gold_v2_13d2_tier2_source_rows.csv
gold_v2_13d2_tier2_final_sot_rows.csv
gold_v2_13d2_tier2_manifest_match_rows.csv
gold_v2_13d2_tier2_manifest_mismatch_rows.csv
gold_v2_13d2_tier2_final_manifest_mismatch_rows.csv
gold_v2_13d2_tier2_feature_range_by_match_status.csv
gold_v2_13d2_tier2_feature_range_by_final_status.csv
gold_v2_13d2_tier2_variant_candidate_conditions.csv
gold_v2_13d2_tier2_reconciliation_decision_matrix.csv
gold_v2_13d2_tier2_blockers.csv
```

---

## 9. 13D2成功条件

```text
1. TIER2_HVT source 31件を match 19 / mismatch 12 に分解できる
2. final SOT TIER2 13件を match 2 / mismatch 11 に分解できる
3. mismatch 12件のfeature範囲を説明できる
4. 単一条件修正 / variant分割 / historical-only のいずれかを決定できる
5. patchを出す場合も audit-only preview に留める
6. external actionsは全てfalse
```

---

## 10. 13D2停止条件

```text
13D出力が見つからない
TIER2 source rows が31件でない
TIER2 final rows が13件でない
manifest mismatch 12 / final mismatch 11 が再現しない
必要feature列がない
単一条件/variant候補で説明できない
```

停止した場合は、live条件を作らない。

---

## 11. 13D2以降のロードマップ

### 13D3

13D2結果で分岐。

```text
13D3_FREEZE_MEDIUM_TIER2_HVT_RECONCILED_RULE_AUDIT_ONLY
13D3_SPLIT_MEDIUM_TIER2_HVT_VARIANTS_AUDIT_ONLY
13D3_MEDIUM_TIER2_HVT_HISTORICAL_ONLY_BLOCK_AUDIT_ONLY
```

### 13E

```text
13E_MEDIUM_FEATURE_ASOF_PARITY_PREFLIGHT_AUDIT_ONLY
```

MEDIUMのfeature/asofを確認。

### 13F

```text
13F_BUILD_COMPONENT_LIVE_ELIGIBILITY_MATRIX_AUDIT_ONLY
```

CoreA/CoreB/MEDIUMのlive可否をmatrix化。

### 13G

```text
13G_COMBINED_DRY_RUN_EVALUATOR_DESIGN_AUDIT_ONLY
```

live eligible componentsだけでruntime evaluator設計。

### 14A〜14D

```text
14A_RUNTIME_LIVE_CANDIDATE_EVALUATOR_DRY_RUN_ONLY
14B_DISCORD_NOTIFICATION_PREVIEW_DRY_RUN_ONLY
14C_MT5_ORDER_REQUEST_PREVIEW_DRY_RUN_ONLY
14D_DRY_RUN_PARITY_AND_SAFETY_GATE_AUDIT_ONLY
```

### 15A〜15E

ユーザー明示許可後のみ。

```text
15A_DISCORD_SEND_SANDBOX_OR_TEST_CHANNEL_AUDIT_ONLY
15B_MT5_CONNECTION_AND_ACCOUNT_STATE_AUDIT_ONLY
15C_MT5_ORDER_SEND_DEMO_GUARDED_AUTOTRADE_TEST
15D_MT5_POSITION_MONITOR_AND_CLOSE_AUDIT
15E_DISCORD_TRADE_LIFECYCLE_NOTIFICATION
```

### 16A〜16C

本番はデモ検証後、ユーザー明示許可後のみ。

```text
16A_LIVE_ACCOUNT_READINESS_AND_RISK_ACCEPTANCE_AUDIT
16B_LIVE_GUARDED_AUTOTRADE_MINIMUM_RISK_ROLLOUT
16C_LIVE_AUTOTRADE_WEEKLY_PERFORMANCE_AUDIT
```

---

## 12. 最終完成形

中間目標:

```text
GOLD_V2_LIVE_DRY_RUN_EVALUATOR_READY_NO_EXTERNAL_ACTIONS
```

最終目標:

```text
GOLD_V2_DISCORD_NOTIFIED_MT5_GUARDED_AUTOTRADE_READY
```

---

## 13. 次チャット冒頭に貼る文面

```text
repo: knitanr-a11y/xauusd-signal-lab

以下のハンドオフを読んで続きからお願いします。

必読:
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_13A_13D_MEDIUM_TIER2_RECONCILIATION_20260605.md
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_COMPLETION_ROADMAP_ADDENDUM_20260605.md
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_OHLC_LIVE_EVALUATOR_REPRODUCTION_20260605.md

重要:
今からやることは、source ledgerを読むだけではなく、
OHLCからlive evaluatorとしてfeature/rule/candidateを再計算し、
CoreA/B/MEDIUMのSOT結果にどこまで一致できるかを監査することです。

現在位置:
13Dまで完了。
CoreAはA gate未凍結でlive blocked。
CoreBはsame_count/cluster_id元クラスタリング未復元でhistorical SOT only / live blocked。
MEDIUMはarbitration replayがfinal SOT 87件と一致。ただしTIER2_HVT manifest mismatchが残っています。

次にやること:
13D2_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY

最終完成形:
Discord通知 + MT5 guarded autotrading。
ただし現時点ではaudit-onlyで、Discord/MT5/AI/live hookはまだ禁止です。

禁止:
近似実装禁止。
OHLCから新規探索禁止。
SOT/source ledgerをsource of truthにしてください。
フォルダ名・BAT名・レポート名は 13D2 / 14A のように番号を先頭に入れてください。
```
