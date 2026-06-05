# GOLD V2 13D2 specification — MEDIUM TIER2_HVT source definition reconciliation audit-only

作成日: 2026-06-05  
repo: `knitanr-a11y/xauusd-signal-lab`  
工程名: `13D2_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY`

---

## 1. 目的

13Dで確認済みのMEDIUM arbitration replayはfinal SOT 87件と一致している。  
ただし `TIER2_HVT` は `frozen_medium_rules_20260603.json` のmanifest定義とsource実績が一致していない。

13D2では、13D出力をsource of truthとして、以下をaudit-onlyで分解する。

```text
TIER2_HVT source 31件
TIER2_HVT final SOT 13件
source manifest match 19件 / mismatch 12件
final manifest match 2件 / mismatch 11件
```

この工程では、TIER2_HVTを単一条件修正で扱うべきか、variant分割すべきか、historical-onlyとして止めるべきかを判定するための監査材料を作る。

---

## 2. 絶対禁止

```text
OHLCから新規探索しない
近似条件を採用しない
source ledgerにない条件を作らない
Discord通知しない
MT5発注しない
AI APIを呼ばない
live hookに接続しない
```

13D2は、OHLC live evaluator本体ではない。  
OHLCからのfeature/rule/candidate再計算は後続13E以降で、SOT定義が整理されたcomponentだけを対象にする。

---

## 3. Source of truth

優先SOTは13D出力である。

```text
Files\FX_OUTPUTS\gold_v2_13d_medium_feature_arbitration_audit_only\gold_v2_13d_medium_source_rows_with_manifest_match.csv
Files\FX_OUTPUTS\gold_v2_13d_medium_feature_arbitration_audit_only\gold_v2_13d_medium_recomputed_final_rows.csv
Files\FX_OUTPUTS\gold_v2_13d_medium_feature_arbitration_audit_only\gold_v2_13d_medium_final_sot_rule_summary.csv
Files\FX_OUTPUTS\gold_v2_13d_medium_feature_arbitration_audit_only\gold_v2_13d_medium_rule_manifest_inventory.csv
Files\FX_OUTPUTS\gold_v2_13d_medium_feature_arbitration_audit_only\gold_v2_13d_medium_rule_manifest_coverage.csv
```

参照のみ:

```text
configs\gold_v2\frozen_medium_rules_20260603.json
Files\FX_OUTPUTS\gold_v2_final_portfolio_sot_freeze_audit_only\gold_v2_final_portfolio_2025_2026_sot_ledger.csv
```

---

## 4. 入力CSV仕様

### 4.1 `gold_v2_13d_medium_source_rows_with_manifest_match.csv`

用途:

```text
MEDIUM source 118件のうち、TIER2_HVT source 31件を抽出する。
13Dが付与した own_manifest_match をSOTとして扱う。
```

必須列:

```text
component
own_manifest_match
range96
trend_eff96
ret96
tr_mean_32
regime
dataset
entry_time または top_entry_time
direction または top_direction
profit_r または selected_profit_r または profit
```

優先確認列:

```text
top_candidate_id
top_variant
top_direction
entry_month
```

存在しない優先確認列はOHLCから作り直さない。  
必須列が欠ける場合は `MISSING_SOURCE_FIELD_AUDIT_ONLY` で停止する。

### 4.2 `gold_v2_13d_medium_recomputed_final_rows.csv`

用途:

```text
MEDIUM internal priorityとHIGH arbitration後に残ったfinal MEDIUM 87件から、
TIER2_HVT final 13件を抽出する。
```

### 4.3 manifest関連CSV

用途:

```text
13Dが使ったmanifest条件とcoverageを確認する。
TIER2_HVTの条件キーを読み、mismatch行がどの条件から外れたかを診断する。
```

---

## 5. strategy_id / entry_time / direction / TP-SL / outcome

13D2は新規トレード検出ではないため、TP/SLをOHLCから再計算しない。

```text
strategy_id:
  TIER2_HVT
  top_variant が存在する場合は TIER2_HVT|<top_variant>
  top_candidate_id が存在する場合はさらに |<top_candidate_id> を付与

entry_time:
  13D出力の entry_time を使用
  entry_time がなければ top_entry_time を使用

direction:
  13D出力の direction を使用
  direction がなければ top_direction を使用

TP/SL:
  13D2では再計算しない
  outcome sourceは profit_r / selected_profit_r / profit

outcome:
  profit_r > 0  => WIN
  profit_r < 0  => LOSS
  profit_r == 0 => BREAKEVEN
```

---

## 6. 期待件数

13Dから引き継ぐ期待件数は固定。

```text
TIER2_HVT source rows = 31
TIER2_HVT final SOT rows = 13
TIER2_HVT source manifest match rows = 19
TIER2_HVT source manifest mismatch rows = 12
TIER2_HVT final manifest match rows = 2
TIER2_HVT final manifest mismatch rows = 11
```

これが一致しない場合、13D2は停止し、live条件は作らない。

---

## 7. 監査方法

1. 13D出力CSVの存在、行数、列数、SHA256を `gold_v2_13d2_input_audit.csv` に出す。
2. `component == TIER2_HVT` でsource 31件を抽出する。
3. `own_manifest_match` をSOTとして、match 19件 / mismatch 12件へ分解する。
4. 13D recomputed final rowsからTIER2_HVT final 13件を抽出する。
5. final 13件をmanifest match 2件 / mismatch 11件へ分解する。
6. manifest条件キーを読み、mismatch行ごとに失敗条件セットを付与する。
7. `range96 / trend_eff96 / ret96 / tr_mean_32 / regime / direction / dataset` の範囲を、match/mismatchおよびfinal retained/dropped別に集計する。
8. failed-condition-set、dataset、regime、direction、top_variant別にvariant候補を作る。
9. patch案が出る場合も `patch_preview.json` に留め、configは書き換えない。
10. `decision_matrix.csv` で次工程を以下のどれかに分岐する。

```text
13D3_FREEZE_MEDIUM_TIER2_HVT_RECONCILED_RULE_AUDIT_ONLY
13D3_SPLIT_MEDIUM_TIER2_HVT_VARIANTS_AUDIT_ONLY
13D3_MEDIUM_TIER2_HVT_HISTORICAL_ONLY_BLOCK_AUDIT_ONLY
STOP_REVIEW_13D_OUTPUTS_BEFORE_13D3
```

---

## 8. 出力フォルダ

```text
Files\FX_OUTPUTS\gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only
```

---

## 9. 出力ファイル

最初に見るファイル:

```text
GOLD_V2_13D2_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY_REPORT.md
gold_v2_13d2_medium_tier2_hvt_reconciliation_summary.json
```

補助ファイル:

```text
gold_v2_13d2_input_audit.csv
gold_v2_13d2_tier2_expected_count_checks.csv
gold_v2_13d2_tier2_source_rows.csv
gold_v2_13d2_tier2_final_sot_rows.csv
gold_v2_13d2_tier2_manifest_match_rows.csv
gold_v2_13d2_tier2_manifest_mismatch_rows.csv
gold_v2_13d2_tier2_final_manifest_mismatch_rows.csv
gold_v2_13d2_tier2_feature_range_by_match_status.csv
gold_v2_13d2_tier2_feature_range_by_final_status.csv
gold_v2_13d2_tier2_categorical_summary_by_match_status.csv
gold_v2_13d2_tier2_variant_candidate_conditions.csv
gold_v2_13d2_tier2_reconciliation_decision_matrix.csv
gold_v2_13d2_tier2_blockers.csv
gold_v2_13d2_tier2_mismatch_examples.csv
gold_v2_13d2_tier2_match_vs_mismatch_diff_summary.csv
gold_v2_13d2_tier2_candidate_rule_manifest_patch_preview.json
```

ZIP:

```text
Files\FX_OUTPUTS\gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit.zip
```

---

## 10. 成功条件

```text
TIER2_HVT source 31件を match 19 / mismatch 12 に分解できる
TIER2_HVT final SOT 13件を match 2 / mismatch 11 に分解できる
mismatch 12件のfeature範囲と失敗条件セットを説明できる
単一条件修正 / variant分割 / historical-only の次工程をdecision matrixで明示できる
patch案はaudit-only previewに留める
external actionsは全てfalse
```

---

## 11. 停止条件

```text
13D出力が見つからない
TIER2_HVT source rows が31件でない
TIER2_HVT final rows が13件でない
manifest mismatch 12件 / final mismatch 11件が再現しない
必要feature列がsourceに存在しない
```

停止した場合は、live用条件を作らない。

---

## 12. AI API

```text
AI APIを呼ばない
group評価をしない
component評価をしない
review-target allを使わない
```

13D2はCSV監査のみ。

---

## 13. 実装ファイル

本体:

```text
scripts\gold_v2_runtime\audit_gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only.py
```

BAT:

```text
scripts\gold_v2_runtime\bat\13D2_AUDIT_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY.bat
```

---

## 14. BAT実行順

前提として13Dが実行済みで、13D出力フォルダが存在すること。

```bat
scripts\gold_v2_runtime\bat\13D_AUDIT_MEDIUM_FEATURE_ARBITRATION_AUDIT_ONLY.bat
scripts\gold_v2_runtime\bat\13D2_AUDIT_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY.bat
```

13D2のみを再実行する場合:

```bat
scripts\gold_v2_runtime\bat\13D2_AUDIT_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY.bat
```

---

## 15. 実装内容記録

今回追加するもの:

```text
13D2仕様書
13D2 audit-only Python本体
13D2 audit-only BAT
```

実装する処理:

```text
13D出力をSOTとしてTIER2_HVT source/final rowsを抽出
match/mismatch期待件数を強制監査
manifest失敗条件セットを付与
feature range / categorical summary / variant candidatesを出力
audit-only patch preview JSONを出力
decision matrixとblockersを出力
report / summary / zipを出力
```

実装しない処理:

```text
OHLCからの新規探索
TIER2_HVT configの書き換え
Discord送信
MT5発注
AI API呼び出し
live hook接続
```

---

## 16. 実行してはいけないこと

```text
13D2結果だけでDiscord/MT5/live evaluatorをONにしない
TIER2_HVT mismatchを無視して14Aへ進まない
patch_preview.jsonを本番configとして扱わない
CoreB same_countを近似してHIGH arbitrationに混ぜない
```
