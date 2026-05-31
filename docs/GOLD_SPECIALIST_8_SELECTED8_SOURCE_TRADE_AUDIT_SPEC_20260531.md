# GOLD specialist 8 selected_8 / source trade audit-only 実装仕様

作成日: 2026-05-31
対象: `gold_specialist_8` / selected_8定義 / 探索済みsource trade ledger / audit-only

## 1. 実装名

`GOLD specialist 8 selected_8 source-of-truth rebuild audit-only`

## 2. 目的

前回のAI評価導線では、探索CSVをsource of truthにせず、OHLCから近似再検出したため、探索時の8候補とAI評価対象がズレた。

今回の実装では、OHLC再検出を禁止し、探索済みCSVだけをsource of truthとして以下を作る。

1. 探索CSV棚卸しJSON
2. `selected_8_strategies.csv`
3. 探索済みsource trade ledger
4. source trade audit-only JSON

現時点ではAI APIを呼ばない。

## 3. 対象ファイル

追加するファイル:

```text
docs/GOLD_SPECIALIST_8_SELECTED8_SOURCE_TRADE_AUDIT_SPEC_20260531.md
scripts/gold_specialist_8/build_gold_specialist_8_selected8_source_trades.py
scripts/gold_specialist_8/audit_gold_specialist_8_selected8_source_trades.py
scripts/gold_specialist_8/run_gold_specialist_8_selected8_build_and_audit_ONLY_NO_API.bat
```

作成される出力:

```text
data/gold_specialist_8/config/selected_8_strategies.csv
data/gold_specialist_8/verification/source_inventory/gold_specialist_8_selected8_source_inventory.json
data/gold_specialist_8/verification/trade_outcomes/gold_specialist_8_selected8_source_trade_ledger.csv
data/gold_specialist_8/verification/trade_outcomes/gold_specialist_8_selected8_source_trade_audit.json
```

## 4. 入力CSV

探索サマリー候補CSV:

```text
data/gold_new_signal_candidate_backtest_v10_no_weekday_safe_hours_numpy/gold_candidate_v10_recommended_no_weekday_safe_hours.csv
data/gold_new_signal_candidate_backtest_v10_no_weekday_safe_hours_numpy/gold_candidate_v10_high_pf_no_weekday_safe_hours.csv
data/gold_new_signal_candidate_backtest_v10_no_weekday_safe_hours_numpy/gold_candidate_v10_low_sl_no_weekday_safe_hours.csv
data/gold_new_signal_candidate_backtest_v9_jst_multiview_specialists_fast/gold_candidate_v9_auto_specialist_candidate_pack_jst_corrected.csv
```

探索済みトレードCSV:

```text
data/gold_new_signal_candidate_backtest_v10_no_weekday_safe_hours_numpy/**/*.csv
data/gold_new_signal_candidate_backtest_v9_jst_multiview_specialists_fast/**/*.csv
```

上記のうち、`entry_time` / `direction` / `outcome` / `strategy_id`相当列を持つCSVだけを探索済みトレードCSV候補として扱う。

## 5. source of truth

source of truthは探索CSVだけ。

許可:

```text
探索CSVに存在する strategy_id / source_strategy_id / entry_time / direction / TP / SL / outcome / expected_trades をそのまま使う
```

禁止:

```text
OHLCを読み込んでシグナルを再検出する
手書きStrategySpecで条件を再構成する
strategy_idを記憶や推測で別名変換する
TP/SL/exit_model/JST時間帯を近似再実装する
```

## 6. selected_8定義

`selected_8_strategies.csv` の列:

```text
selected_id
source_file
source_strategy_id
strategy_base
exit_model
direction
jst_hours
weekday_filter
safe_open_excluded
expected_trades
expected_wr
expected_pf
expected_test_pf
notes
```

`source_strategy_id` は探索CSVに存在するIDをそのまま入れる。
`expected_trades` / `expected_wr` / `expected_pf` / `expected_test_pf` は探索サマリーCSVの値をそのまま入れる。
探索CSV側の列名が異なる場合は、スクリプトの列名候補から正規化する。

## 7. 評価対象

この段階の評価対象は、selected_8に含まれる各候補の探索済みsource tradeのみ。

group化はしない。
component評価もしない。
AI review payloadも作らない。

## 8. 除外対象

除外するもの:

```text
OHLCから再検出した行
group ledger
component ledger
既存 validation_trade_outcome_ledger.csv
AI review payload
AI review ledger更新
MT5発注
Discord送信
```

## 9. 期待件数

固定期待件数:

```text
selected strategy count = 8
selected_8_strategies.csv rows = 8
source trade ledger strategy_id種類 = 8
AI API calls = 0
MT5 order sends = 0
Discord sends = 0
```

探索CSV依存の期待件数:

```text
strategy別 source trade rows = selected_8_strategies.csv.expected_trades
source trade ledger total rows = sum(selected_8_strategies.csv.expected_trades)
```

GitHub上では探索CSV本体を取得できない場合があるため、実際の `expected_trades` 数値は生成時に探索サマリーCSVから読み取り、`selected_8_strategies.csv` と audit JSON に固定する。
この数値を人間の記憶や前回ログから手入力しない。

## 10. 監査方法

監査では以下を必ず表示・保存する。

```text
source summary files found/missing
source trade files found
selected rows
source rows
strategy_id別 expected_trades
strategy_id別 source trade rows
missing selected strategy_id
missing source trade strategy_id
count mismatch
required columns missing
entry_time missing
TP/SL missing or abnormal
outcome missing/unresolved count
review ledger rows
AI API call flag
```

## 11. 実行BAT

実行順:

```text
scripts\gold_specialist_8\run_gold_specialist_8_selected8_build_and_audit_ONLY_NO_API.bat
```

このBATは以下を順番に実行する。

```text
python scripts\gold_specialist_8\build_gold_specialist_8_selected8_source_trades.py
python scripts\gold_specialist_8\audit_gold_specialist_8_selected8_source_trades.py --require-all-8 --require-count-match
```

## 12. APIを呼ぶか

呼ばない。

```text
OpenAI API: 呼ばない
MT5発注: しない
Discord送信: しない
```

## 13. 成功条件

成功条件:

```text
探索サマリーCSVが存在する
selected_8_strategies.csv が8行で生成される
全selected strategyが探索サマリーCSVから取得されている
source trade ledgerが探索済みトレードCSVからのみ生成される
source trade ledgerが8 strategyすべてを含む
strategy別行数が expected_trades と一致する
entry_time / direction / TP / SL / outcome が監査可能
AI review ledger rows が表示される
AI API calls が0である
```

## 14. 停止条件

以下の場合は停止する。

```text
探索サマリーCSVが見つからない
selected_8が8行に満たない、または重複する
selected_8のsource_strategy_idが探索CSVから特定できない
探索済みトレードCSVが見つからない
source trade ledgerに8 strategyが揃わない
strategy別 source trade rows が expected_trades と一致しない
entry_time / direction / outcome が欠ける
TP/SLが両方とも欠ける、または方向と価格関係が明らかに異常
AI APIを呼ぶ設定が混入している
OHLC CSVを入力に要求している
```

## 15. 見るべきファイル

```text
docs/GOLD_SPECIALIST_8_POSTMORTEM_AI_REVIEW_AND_IMPLEMENTATION_RULES_20260531.md
docs/NEXT_CHAT_HANDOFF_GOLD_SPECIALIST8_SELECTED8_REBUILD_20260531.md
docs/GOLD_SPECIALIST_8_SELECTED8_SOURCE_TRADE_AUDIT_SPEC_20260531.md
data/gold_specialist_8/config/selected_8_strategies.csv
data/gold_specialist_8/verification/source_inventory/gold_specialist_8_selected8_source_inventory.json
data/gold_specialist_8/verification/trade_outcomes/gold_specialist_8_selected8_source_trade_ledger.csv
data/gold_specialist_8/verification/trade_outcomes/gold_specialist_8_selected8_source_trade_audit.json
```

## 16. 既知の注意点

- GitHub上で探索CSV本体が取得できない場合、生成と監査はユーザーのローカル環境で実行する必要がある。
- source_strategy_idは探索CSVに存在する値を使う。別名変換はしない。
- 既存のvalidation backtest / AI review BATは、source trade audit-onlyが成功するまで使わない。

## 17. 次にやること

1. ユーザー環境で audit-only BAT を実行する。
2. `selected_8_strategies.csv` と audit JSON の strategy別件数を確認する。
3. count mismatch がゼロになってから、別仕様書で group aggregation を設計する。
4. AI評価はさらに後段。現時点では実行禁止。
