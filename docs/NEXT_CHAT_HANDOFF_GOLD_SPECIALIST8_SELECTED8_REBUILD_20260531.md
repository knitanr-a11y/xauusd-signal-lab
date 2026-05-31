# NEXT CHAT HANDOFF - GOLD specialist 8 selected_8再構築 / AI評価事故後の引き継ぎ

作成日: 2026-05-31
repo: `knitanr-a11y/xauusd-signal-lab`

## 0. 新チャットで最初に読むべきドキュメント

必ず最初に読むこと。

```text
docs/GOLD_SPECIALIST_8_POSTMORTEM_AI_REVIEW_AND_IMPLEMENTATION_RULES_20260531.md
```

このドキュメントには、今回のAI評価導線の事故原因、再発防止、今後の実装順、仕様書作成ルールがまとまっている。

## 1. 現在の結論

現時点では、`gold_specialist_8` のAI評価はまだ実行してはいけない。

理由:

```text
AI review rows は 0
group rows が 1,720 と多すぎる
expected strategies present in GROUP が 4/8
SELL_RSI50_RECLAIM に偏りすぎ
探索CSVをsource of truthにしたledgerではない
```

今回の根本原因は、探索で得た候補をそのままAI評価へ渡さず、探索結果を見て別ロジックとして近似実装してしまったこと。

## 2. 現在の監査結果

固定版バックテスト後:

```text
cycle_ok: true
run_dir: data\gold_specialist_8\verification\backtests\2026\05\20260531_124608
m15_rows_used: 29816
raw_component_signals: 1729
groups: 1720
component_rows: 1729
review_input_rows: 3449
buy_sell_conflict_skipped_groups: 0
```

監査結果:

```text
trade outcome rows : 3449
group rows         : 1720
component rows     : 1729
AI review rows     : 0
expected strategies present in GROUP: 4/8
```

GROUP strategy counts:

```text
1247 SELL_H1H4_TREND_M15_RSI50_RECLAIM_ADX10_BLEND_STRUCT_H1ATR_RR2_MIN50_CAP240_JST23_04
 387 BUY_H1_IMPULSE_M15_EMA20_REJECT_ADX10_H1ATR_TP15_RR2_MIN50_CAP220_JST23_04
  80 SELL_H1H4_TREND_M15_EMA34_REJECT_ADX10_H4ATR_TP075_RR2_MIN50_CAP250_JST10_11
   6 BUY_H1_DONCH72_ADX18_STRUCT_RR2_MIN50_CAP220
```

Missing:

```text
BUY_H1_DONCH72_ADX10_H4ATR_TP055_RR18_MIN50_CAP220
SELL_H1_DONCH36_ADX10_TP150_SL75_JST20_22
SELL_H1_DONCH72_ADX10_TP50_SL25_JST18_22
BUY_H1_DONCH20_ADX10_BLEND_STRUCT_H1ATR_RR2_MIN50_CAP240_JST01_05
```

## 3. 絶対に今実行しないもの

評価対象が正しくないため、以下は当面実行しない。

```text
scripts/gold_specialist_8/run_gold_specialist_8_validation_ai_review.bat
scripts/gold_specialist_8/run_gold_specialist_8_validation_ai_review_REAL_GROUP_ALL_LOCKED_REQUIRE8.bat
scripts/gold_specialist_8/run_gold_specialist_8_validation_ai_review_REAL_GROUP20_LOCKED.bat
```

理由:

- まだ探索時の8候補と一致したledgerがない
- group/componentの意味が混在している
- strategy構成が4/8しか出ていない
- `SELL_RSI50_RECLAIM` の件数が異常に多い

## 4. すでに追加済みの主なファイル

### 4.1 事故原因・再発防止ドキュメント

```text
docs/GOLD_SPECIALIST_8_POSTMORTEM_AI_REVIEW_AND_IMPLEMENTATION_RULES_20260531.md
```

内容:

- なぜ事故が起きたか
- なぜ探索結果とAI評価対象がズレたか
- 今後の実装ルール
- カスタム指示に貼る文章
- 今後のPhase別実装フロー
- 仕様書に必ず書く項目

### 4.2 監査BAT / 監査Python

```text
scripts/gold_specialist_8/audit_gold_specialist_8_validation_targets.py
scripts/gold_specialist_8/run_gold_specialist_8_validation_ai_review_AUDIT_ONLY_NO_API_V2.bat
```

目的:

- APIを呼ばずに、group/component/AI review rows/strategy_id別件数を表示
- 8候補がgroupに揃っているか確認

注意:

- 現行の監査はGROUP leader strategy_idを見る。
- component側の件数表示は今後拡張すべき。

### 4.3 Donchian列merge修正版

```text
scripts/gold_specialist_8/run_gold_specialist_8_validation_backtest_FIXED_HTF_DONCHIAN.py
scripts/gold_specialist_8/run_gold_specialist_8_validation_backtest_FIXED_HTF_DONCHIAN.bat
```

目的:

- 初期実装でH1 Donchian列がM15 contextへ渡っていなかった問題を修正。

結果:

- Donchian系は一部復活したが、まだ8候補評価としては成立していない。
- group 1,720件、4/8のみ。

## 5. 今回の根本原因

### 5.1 探索CSVをsource of truthにしなかった

本来は探索時のCSV/ledgerをそのままAI評価に渡すべきだった。

間違った流れ:

```text
OHLC再読み込み
-> 手書きStrategySpecで近似再検出
-> 新しいgroup/component ledger生成
-> AI評価payload生成
```

正しい流れ:

```text
探索CSV / 探索済みtrade ledger
-> selected_8定義
-> source trade ledger
-> audit-only
-> AI評価
```

### 5.2 RSI50_RECLAIMが状態判定になっている

現行ロジックは、RSIが50未満かつcloseがEMA20未満なら発火し続ける状態に近い。

本来はイベント条件にすべき。

```text
previous_rsi >= 50 and current_rsi < 50
```

### 5.3 groupとcomponentを混ぜた

初回AI評価はgroup onlyで良い。
component評価は後段で、負けgroup・重複group・特定strategyだけに限定する。

### 5.4 AI評価BATに安全装置が不足していた

不足していたもの:

- audit-only強制
- strategy構成チェック
- pending件数チェック
- lock
- max-itemsまたは明示的全件許可条件
- review-target all禁止

## 6. 新チャットでやるべき実装順

### Phase 1: 探索CSVの棚卸し

まず探索結果CSVを正として確認する。

候補:

```text
data/gold_new_signal_candidate_backtest_v10_no_weekday_safe_hours_numpy/gold_candidate_v10_recommended_no_weekday_safe_hours.csv
data/gold_new_signal_candidate_backtest_v10_no_weekday_safe_hours_numpy/gold_candidate_v10_high_pf_no_weekday_safe_hours.csv
data/gold_new_signal_candidate_backtest_v10_no_weekday_safe_hours_numpy/gold_candidate_v10_low_sl_no_weekday_safe_hours.csv
data/gold_new_signal_candidate_backtest_v9_jst_multiview_specialists_fast/gold_candidate_v9_auto_specialist_candidate_pack_jst_corrected.csv
```

確認すること:

```text
strategy_id
strategy_base
direction
exit_model
jst_hours
weekday_filter
safe_open_excluded
expected_trades
WR / PF / Test PF
source file
```

### Phase 2: selected_8定義ファイルを作る

作成予定:

```text
data/gold_specialist_8/config/selected_8_strategies.csv
```

列:

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

これを唯一のselected_8定義にする。

### Phase 3: 探索済みsource trade ledgerを作る

ローソク足から再検出しない。
探索時に出たresolved trades CSVを使う。

作成予定:

```text
data/gold_specialist_8/verification/trade_outcomes/gold_specialist_8_selected8_source_trade_ledger.csv
```

この段階ではgroup化しない。

### Phase 4: source trade audit-only

作成予定:

```text
scripts/gold_specialist_8/audit_gold_specialist_8_selected8_source_trades.py
scripts/gold_specialist_8/run_gold_specialist_8_selected8_source_audit_ONLY_NO_API.bat
```

監査項目:

```text
8候補すべて存在するか
候補別件数がexpected_tradesと近いか
direction一致
exit_model一致
TP/SL異常なし
unresolved過多なし
AI review ledger状態
```

### Phase 5: source trade AI評価

初回AI評価はsource trade onlyまたはgroup only。

禁止:

```text
review-target all
component全件評価
監査なし全件評価
```

### Phase 6: group aggregation

source tradeが正しく再現できた後で、初めてgroup化する。

作成予定:

```text
data/gold_specialist_8/verification/trade_outcomes/gold_specialist_8_selected8_group_trade_ledger.csv
data/gold_specialist_8/verification/trade_outcomes/gold_specialist_8_selected8_component_signal_ledger.csv
```

仕様:

```text
same M15 close_time
same direction
leader priority from selected_8 config
different family vote +1
same family vote +0.5
low SL SELL cap
BUY/SELL同時はskipまたは別監査
```

## 7. 新チャットで最初に指示する文章

新チャットで以下を貼る。

```text
repo: knitanr-a11y/xauusd-signal-lab

まず docs/GOLD_SPECIALIST_8_POSTMORTEM_AI_REVIEW_AND_IMPLEMENTATION_RULES_20260531.md と docs/NEXT_CHAT_HANDOFF_GOLD_SPECIALIST8_SELECTED8_REBUILD_20260531.md を読んでください。

前回、gold_specialist_8 のAI評価導線で、探索結果をsource of truthにせず近似再実装してしまい、評価対象が探索時の8候補とズレました。現時点ではAI評価は実行禁止です。

次にやることは、探索CSVをsource of truthとして selected_8_strategies.csv を作り、探索済みsource trade ledgerを作ることです。OHLCから再検出しないでください。まず探索CSVの棚卸し、selected_8定義、source trade audit-onlyまで進めてください。

実装前に必ず仕様書を書き、どの入力CSVを使うか、どの出力を作るか、期待件数、成功条件、停止条件、AI APIを呼ぶかどうかを明記してください。
```

## 8. カスタム指示に貼る短縮版

```text
FX/GOLD/BTCの検証・自動売買・AI評価を実装するときは、探索結果や既存CSVを必ずsource of truthとして扱うこと。探索で得た候補を、記憶や要約から別ロジックとして近似再実装してはいけない。実装前に必ず仕様書を作り、入力CSV、出力CSV、strategy_id、entry_time、direction、TP/SL、outcome、期待件数、監査方法、AI APIを呼ぶかどうかを明記すること。

AI評価を実行するBAT/スクリプトでは、必ずAPI実行前にaudit-onlyを通すこと。auditではsource rows、group rows、component rows、strategy_id別件数、期待strategyの存在、pending件数、review ledger行数を表示すること。期待件数やstrategy構成が探索結果と一致しない場合はAPIを呼ばず停止すること。

group評価とcomponent評価は必ず分離すること。初回AI評価はgroup onlyを原則とし、component評価やall評価は、負けgroup・重複group・特定strategyなどに限定した別BATでのみ行うこと。`review-target all` や上限なしAPI評価は、明示的な危険名と事前監査なしに作成・実行してはいけない。
```
