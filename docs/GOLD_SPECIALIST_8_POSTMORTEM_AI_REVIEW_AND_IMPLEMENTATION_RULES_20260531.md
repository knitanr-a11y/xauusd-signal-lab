# GOLD specialist 8 事故原因分析・再発防止・実装仕様ルール

作成日: 2026-05-31
対象: `gold_specialist_8` / 新8シグナル / 検証生成 / AI評価導線

## 1. 結論

今回の問題は、OpenAI API評価そのものより前段の **評価対象生成** が根本的に誤っていたことが主因である。

最も重大な失敗は、探索で得た候補トレード・候補定義をそのままAI評価へ渡すべきところを、探索結果を見て別ロジックとして近似実装し直したことである。その結果、探索時の件数・条件・strategy_id・時間帯・exit model と、AI評価対象として作成したledgerが一致しなくなった。

さらに、AI評価BATに `--max-items`、同時起動ロック、評価対象監査、8候補整合チェックを初期実装していなかったため、大量payload作成とAPI料金増加のリスクを生んだ。

## 2. 実際に起きたこと

### 2.1 AI評価payloadが大量に作成された

`trade_ai_review_payloads_summary.json` では以下が確認された。

```text
rows_in: 1458
rows_out: 1458
```

これは本来の「少量確認」ではなく、1,458件のAI評価payloadを作成したことを意味する。

### 2.2 その後の固定版検証でも対象が多すぎた

固定版バックテスト後のsummary:

```text
m15_rows_used: 29816
raw_component_signals: 1729
groups: 1720
component_rows: 1729
review_input_rows: 3449
buy_sell_conflict_skipped_groups: 0
```

groupが1,720件あり、探索時に想定していた8候補の厳選評価規模と大きくズレていた。

### 2.3 8候補が揃っていなかった

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

missing:

```text
BUY_H1_DONCH72_ADX10_H4ATR_TP055_RR18_MIN50_CAP220
SELL_H1_DONCH36_ADX10_TP150_SL75_JST20_22
SELL_H1_DONCH72_ADX10_TP50_SL25_JST18_22
BUY_H1_DONCH20_ADX10_BLEND_STRUCT_H1ATR_RR2_MIN50_CAP240_JST01_05
```

この状態は「8シグナルのAI評価」ではない。

## 3. なぜこのようなことになったか

### 3.1 探索CSVをsource of truthにしなかった

本来は、探索時のCSVに含まれる以下を正とすべきだった。

- source strategy id
- strategy base
- direction
- exit model
- TP/SL model
- JST hour filter
- rollover/safe-open exclusion
- expected trade count
- PF / WR / Test PF
- 実際のentry_time / entry_price / tp / sl / outcome

しかし、実装では探索CSVから直接trade outcome ledgerを作らず、Python側に `StrategySpec` を手書きした。

この時点で、探索時の候補と実装された候補の一致性が失われた。

### 3.2 strategy_idを探索IDから別名に変換した

探索時の候補例:

```text
H1_DONCH72_BREAK_M15_CONT_ADX18__VAR_STRUCT_RR2.0_MIN50_CAP220
H1_DONCH72_BREAK_M15_CONT_ADX10__VAR_H4ATR_TP0.55_RR1.8_MIN50_CAP220
```

実装側の候補例:

```text
BUY_H1_DONCH72_ADX18_STRUCT_RR2_MIN50_CAP220
BUY_H1_DONCH72_ADX10_H4ATR_TP055_RR18_MIN50_CAP220
```

この名称変換を行ったが、変換表・原典CSV・期待件数を仕様として固定していなかった。結果として、どの探索候補を再現しているのか曖昧になった。

### 3.3 探索時のトレード一覧を再利用せず、ローソク足から再検出した

正しい流れ:

```text
探索済みトレードCSV
  -> selected_8定義
  -> AI評価payload
  -> AI tag summary
```

実際にやってしまった流れ:

```text
OHLC再読み込み
  -> 手書きStrategySpecで再検出
  -> 新しいgroup/component ledger作成
  -> AI評価payload作成
```

再検出方式は、探索時と1条件でも違うと件数・勝敗・対象が変わる。今回まさにこの問題が発生した。

### 3.4 Donchian列をHTF contextへ渡していなかった

最初の検証生成器では、H1/H4/D1からM15へasof mergeする列にDonchian列が含まれていなかった。

そのため、Donchian系候補が正しく発火しなかった。

### 3.5 RSI50_RECLAIMをイベントではなく状態として実装した

本来の `RSI50_RECLAIM` / 再下抜けは、クロスイベントであるべき。

正しい例:

```text
previous_rsi >= 50 and current_rsi < 50
```

しかし実装では、以下のような状態条件に近かった。

```text
rsi14 < 50 and close < ema20
```

これにより、RSIが50未満の間ずっと発火し、SELL_RSI50が1,247件まで膨らんだ。

### 3.6 group と component の意味を混同した

- group: 実際に1本の注文として扱う集約トレード
- component: groupに参加した各候補シグナル

初期AI評価では、groupのみを評価すべきだった。component評価は後段で、負けgroup・重複group・特定strategyだけに限定すべきだった。

しかし、`review-target all` により group + component が混在してpayload化された。

### 3.7 AI評価前の安全装置が不足していた

初期BATに不足していたもの:

- 同時起動ロック
- `--max-items` または明示的な全件許可
- API実行前の件数表示
- 8候補整合チェック
- source strategy count audit
- group/component別の件数確認
- pending件数が多すぎる場合の停止
- dry-run/audit-onlyの初回実行強制

そのため、評価対象が間違っていてもAPI実行まで進める構造になっていた。

## 4. 再発防止ルール

### 4.1 source of truthルール

探索結果を使う場合、必ず探索CSVまたは探索トレードledgerをsource of truthにする。

禁止:

```text
探索結果を見て、別ロジックとして近似再実装すること
```

許可:

```text
探索CSVのstrategy_id・entry_time・direction・exit_model・TP/SL・outcomeをそのまま使う
```

### 4.2 変更前に必ず仕様書を書く

コード実装前に以下をMarkdown仕様書に明記する。

- 目的
- 対象ファイル
- 入力データ
- 出力データ
- source of truth
- 評価対象の定義
- 除外対象
- 期待件数
- 監査方法
- 実行BAT
- AI APIを呼ぶかどうか
- APIを呼ぶ場合の上限または全件許可条件

### 4.3 AI API実行前ゲート

AI APIを呼ぶBATは、必ず以下を通過しないと実行不可にする。

- audit-only が成功している
- ledger rows / group rows / component rows が表示されている
- strategy_id別件数が表示されている
- 期待するstrategy_idが揃っている
- 件数が探索時expected rangeから大幅に逸脱していない
- lockが取得できている
- review ledger pathがファイルである
- component評価は明示指定時のみ

### 4.4 group評価とcomponent評価を分離する

初回AI評価:

```text
group only
```

後段AI評価:

```text
component only, but filtered by:
- losing groups only
- overlap groups only
- selected strategy only
- suspicious tags only
```

`all` は原則禁止。使う場合は `DANGEROUS_FULL_ALL` のような明示名にする。

### 4.5 件数ガード

AI評価前に以下を表示する。

```text
source rows
group rows
component rows
pending group rows
pending component rows
expected strategy count
present strategy count
strategy_id counts
estimated max API calls
```

想定件数より大きい場合は停止する。

### 4.6 近似実装禁止

探索結果を実装に移すとき、以下を禁止する。

- strategy名だけ似せる
- 条件を記憶から再構成する
- exit_modelを近似する
- 時間帯フィルターを手入力で再現する
- 探索時の安全時間除外を省略する
- 検証CSVなしでAI評価導線を作る

## 5. カスタム指示に貼る説明文

以下をChatGPTのカスタム指示またはプロジェクト指示へ貼る。

```text
FX/GOLD/BTCの検証・自動売買・AI評価を実装するときは、探索結果や既存CSVを必ずsource of truthとして扱うこと。探索で得た候補を、記憶や要約から別ロジックとして近似再実装してはいけない。実装前に必ず仕様書を作り、入力CSV、出力CSV、strategy_id、entry_time、direction、TP/SL、outcome、期待件数、監査方法、AI APIを呼ぶかどうかを明記すること。

AI評価を実行するBAT/スクリプトでは、必ずAPI実行前にaudit-onlyを通すこと。auditではsource rows、group rows、component rows、strategy_id別件数、期待strategyの存在、pending件数、review ledger行数を表示すること。期待件数やstrategy構成が探索結果と一致しない場合はAPIを呼ばず停止すること。

group評価とcomponent評価は必ず分離すること。初回AI評価はgroup onlyを原則とし、component評価やall評価は、負けgroup・重複group・特定strategyなどに限定した別BATでのみ行うこと。`review-target all` や上限なしAPI評価は、明示的な危険名と事前監査なしに作成・実行してはいけない。

新しい実装を追加したら、必ず仕様書に「何を実装したか」「どのファイルを見るか」「どのBATをどの順番で実行するか」「成功条件」「停止条件」「出力ファイル」を記録すること。ユーザーに説明するときは、できたこと・未確認のこと・実行してはいけないことを分けて説明すること。
```

## 6. 今後の正しい実装フロー

### Phase 0: 現状凍結

当面使わない:

```text
scripts/gold_specialist_8/run_gold_specialist_8_validation_ai_review.bat
scripts/gold_specialist_8/run_gold_specialist_8_validation_ai_review_REAL_GROUP_ALL_LOCKED_REQUIRE8.bat
```

AI評価は、評価対象が確定するまで実行しない。

### Phase 1: 探索CSVの棚卸し

確認対象:

```text
data/gold_new_signal_candidate_backtest_v10_no_weekday_safe_hours_numpy/gold_candidate_v10_recommended_no_weekday_safe_hours.csv
data/gold_new_signal_candidate_backtest_v10_no_weekday_safe_hours_numpy/gold_candidate_v10_high_pf_no_weekday_safe_hours.csv
data/gold_new_signal_candidate_backtest_v10_no_weekday_safe_hours_numpy/gold_candidate_v10_low_sl_no_weekday_safe_hours.csv
data/gold_new_signal_candidate_backtest_v9_jst_multiview_specialists_fast/gold_candidate_v9_auto_specialist_candidate_pack_jst_corrected.csv
```

やること:

- 探索候補IDの確認
- 8候補の出所確認
- expected trades / PF / WR / Test PF の確認
- JST時間帯・曜日有無・rollover除外の確認
- exit_modelの確認

### Phase 2: selected_8定義ファイル作成

作成予定:

```text
data/gold_specialist_8/config/selected_8_strategies.csv
```

最低限の列:

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

このCSVを唯一のselected_8定義とする。

### Phase 3: 探索済みトレードledgerの作成

理想:

探索時に出たresolved trades CSVを直接使う。

作成予定:

```text
data/gold_specialist_8/verification/trade_outcomes/gold_specialist_8_selected8_source_trade_ledger.csv
```

この段階ではgroup化しない。各候補単体のトレードを評価対象とする。

### Phase 4: 単体候補の監査

作成予定:

```text
scripts/gold_specialist_8/audit_gold_specialist_8_selected8_source_trades.py
scripts/gold_specialist_8/run_gold_specialist_8_selected8_source_audit_ONLY_NO_API.bat
```

監査項目:

- 8候補がすべて存在するか
- 候補別件数が探索時 expected_trades と近いか
- directionが一致するか
- exit_modelが一致するか
- TP/SLが異常でないか
- unresolvedが多すぎないか
- AI review ledgerが0または既評価skipできるか

### Phase 5: group aggregationは後段

単体候補が正しく再現できてから、初めてgroup化する。

作成予定:

```text
data/gold_specialist_8/verification/trade_outcomes/gold_specialist_8_selected8_group_trade_ledger.csv
data/gold_specialist_8/verification/trade_outcomes/gold_specialist_8_selected8_component_signal_ledger.csv
```

仕様:

- same M15 close_time
- same direction
- leader priority from selected_8 config
- different family vote +1
- same family vote +0.5
- low SL SELL cap
- BUY/SELL同時はskipまたは別監査

### Phase 6: AI評価

初回AI評価:

```text
selected8 source trade group only or source trade only
```

禁止:

```text
review-target all
component全件評価
監査なし全件評価
```

AI評価後に作成するsummary:

```text
data/gold_specialist_8/verification/ai_review_selected8/trade_ai_review_ledger.jsonl
data/gold_specialist_8/verification/ai_review_selected8/trade_ai_tag_summary.csv
data/gold_specialist_8/verification/ai_review_selected8/strategy_ai_review_summary.csv
```

## 7. 仕様書の書き方ルール

新規実装・修正を行った場合、必ず以下を記載する。

```text
実装名:
目的:
対象ファイル:
入力:
出力:
実行BAT:
APIを呼ぶか:
MT5発注するか:
Discord送信するか:
source of truth:
評価対象:
除外対象:
期待件数:
成功条件:
停止条件:
見るべきファイル:
既知の注意点:
次にやること:
```

この仕様がないままコードを追加してはいけない。

## 8. 現時点の判断

現時点の `gold_specialist_8` AI評価はまだ実行対象として不適切。

理由:

- AI review rows は0
- group rows が1,720と多い
- expected strategies present in GROUP が4/8
- SELL_RSI50_RECLAIMに偏りすぎ
- 探索CSVから直接作ったledgerではない

次にやることは、AI評価ではなく、探索CSVを正としたselected_8定義とsource trade ledgerを作ることである。
