# GOLD V2 13E3 specification — MEDIUM feature source locator audit-only

作成日: 2026-06-05  
工程名: `13E3_MEDIUM_FEATURE_SOURCE_LOCATOR_AUDIT_ONLY`

## 1. 目的

13E2でOHLC formula/asof grid 11,050通りを試したが、source 31件のfeature値を完全再現できなかった。

13E3では、OHLC式を追加で近似するのではなく、ローカルの既存成果物から元feature生成ソース候補を探す。

## 2. source of truth

```text
13D3 source rows 31件
feature columns: range96, ret96, trend_eff96, tr_mean_32, regime
entry_time / direction / strategy_id / profit_r
```

## 3. 探索対象

ローカルの以下を探索する。

```text
repo root
Files root
Files\FX_OUTPUTS
```

対象拡張子:

```text
.csv
.parquet
```

優先ファイル名:

```text
*feature*
*medium*
*coreb*
*ledger*
*candidate*
*rule*
```

## 4. 監査方法

1. candidate file inventoryを作る。
2. time列候補を検出する。
3. feature列候補を検出する。
4. entry_timeで13D3 source rowsへjoinする。
5. `range96 / ret96 / trend_eff96 / tr_mean_32` の一致件数を数える。
6. 完全一致ファイルがあるか判定する。

## 5. 成功条件

```text
source rows 31件
candidate file内にentry_time 31/31が見つかる
4 featureすべて31/31一致する
```

成功してもlive化はしない。次に、そのファイルの生成元コードを確認する。

## 6. 停止条件

```text
candidate fileがない
entry_timeが31/31で揃う候補がない
feature完全一致候補がない
```

## 7. 禁止

```text
OHLCから新規探索しない
source rowsを変更しない
Discord通知しない
MT5発注しない
AI APIを呼ばない
live hookに接続しない
```

## 8. 出力

```text
Files\FX_OUTPUTS\gold_v2_13e3_medium_feature_source_locator_audit_only
```

```text
GOLD_V2_13E3_MEDIUM_FEATURE_SOURCE_LOCATOR_AUDIT_ONLY_REPORT.md
gold_v2_13e3_medium_feature_source_locator_summary.json
gold_v2_13e3_candidate_file_inventory.csv
gold_v2_13e3_candidate_file_scores.csv
gold_v2_13e3_best_candidate_join_rows.csv
gold_v2_13e3_decision_matrix.csv
gold_v2_13e3_blockers.csv
```
