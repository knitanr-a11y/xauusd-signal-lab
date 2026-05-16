# TRADE_AI_REVIEW_JOURNAL_IMPLEMENTATION_NOTES

## 目的

`docs/TRADE_AI_REVIEW_JOURNAL_DESIGN.md` の方針に沿って追加した、GOLD/BTC デモ口座トレードAI評価ジャーナルの初期実装メモ。

この実装は、既存のGOLD/BTCシグナル・自動売買を直接変更しない。
まずは以下を目的にする。

```text
1. MT5の決済済み履歴を取得する
2. 既存order ledgerと結合して factual outcome ledger を作る
3. M15前100本・後20本を中心に feature snapshot を作る
4. AI投入用payloadを作る
5. AIに仮説タグを付けさせる
6. タグ別成績を集計する
7. 将来的にDiscord警告へつなげる
```

重要:

```text
AI評価は仮説タグ付けのみ。
1件の負けでルール変更しない。
勝ちトレードも比較する。
タグ別成績が悪く、さらに仮バックテストで改善確認できるまでフィルタ化しない。
```

---

## 追加ファイル

### 共通ユーティリティ

```text
scripts/trade_ai_review_utils.py
```

役割:

```text
CSV/JSON/JSONL IO
Windows long path対応
時刻パース
方向/銘柄正規化
R計算
outcome分類
OHLCV正規化
ATR/EMA/MACD等の軽量indicator付与
タグ/スキーマ/プロンプトのバージョン定義
```

このファイルはMT5/OpenAIに依存しない。
他のAI review系スクリプトから共通利用する。

---

### Step 1: MT5履歴エクスポート

```text
scripts/export_mt5_closed_trade_history.py
```

役割:

```text
MT5 history_deals_get / history_orders_get を読み取り、以下を出力する。

mt5_history_deals.csv
mt5_history_orders.csv
mt5_history_positions.csv
latest_mt5_closed_trade_history_export.json
```

読み取り専用。
注文送信・変更・決済は行わない。

出力の `mt5_history_positions.csv` は、主に `position_id` 単位でdealをまとめた後続処理用の補助CSV。
完全な戦略ledgerではなく、既存order ledgerと結合するためのMT5履歴側データ。

一行コマンド例:

```bat
python scripts\export_mt5_closed_trade_history.py --out-dir data\runtime_logs\trade_ai_review\mt5_history --lookback-days 30 --symbols "GOLD#,BTCUSD#" --expected-login 75539039
```

---

### Step 2: outcome ledger作成

```text
scripts/build_trade_outcome_ledger_from_order_ledger.py
```

役割:

```text
既存order ledgerと mt5_history_positions.csv を結合して、trade_outcome_ledger.csv を作る。
```

結合優先順位:

```text
1. position_ticket / position_id
2. order_ticket / entry_order_ticket / close_order_ticket
3. deal_ticket / entry_deal_ticket / close_deal_ticket
4. symbol + direction + entry_time近似
```

出力内容:

```text
trade_id
order_key
payload_key
signal_key
strategy_id
condition_id
entry_time
entry_price
sl_price
tp_price
close_time
close_price
profit
profit_r
outcome
close_reason
holding_minutes
match_status
match_method
```

一行コマンド例:

```bat
python scripts\build_trade_outcome_ledger_from_order_ledger.py --order-ledger-csv data\mt5_demo_order_test\goldsharp_auto_trade_demo_prod_order_ledger.csv --order-ledger-csv data\runtime_state\gold\multi_strategy\guarded_demo_order_ledger.csv --mt5-positions-csv data\runtime_logs\trade_ai_review\mt5_history\mt5_history_positions.csv --mt5-deals-csv data\runtime_logs\trade_ai_review\mt5_history\mt5_history_deals.csv --output-csv data\runtime_logs\trade_ai_review\trade_outcome_ledger.csv --output-json data\runtime_logs\trade_ai_review\trade_outcome_ledger_summary.json
```

BTC側ledgerがある場合は `--order-ledger-csv` を追加する。

例:

```bat
python scripts\build_trade_outcome_ledger_from_order_ledger.py --order-ledger-csv data\mt5_demo_order_test\goldsharp_auto_trade_demo_prod_order_ledger.csv --order-ledger-csv data\runtime_state\gold\multi_strategy\guarded_demo_order_ledger.csv --order-ledger-csv data\runtime_state\btc\btc_strategy\guarded_demo_order_ledger.csv --mt5-positions-csv data\runtime_logs\trade_ai_review\mt5_history\mt5_history_positions.csv --mt5-deals-csv data\runtime_logs\trade_ai_review\mt5_history\mt5_history_deals.csv --output-csv data\runtime_logs\trade_ai_review\trade_outcome_ledger.csv --output-json data\runtime_logs\trade_ai_review\trade_outcome_ledger_summary.json
```

---

### Step 3: feature snapshot作成

```text
scripts/build_trade_feature_snapshots.py
```

役割:

```text
各トレードのentry_timeを基準に、M15前100本・後20本、H1/H4/D1前方文脈、M5 first-touch/MFE/MAEを作る。
```

出力:

```text
trade_feature_snapshot.csv
trade_feature_snapshot.jsonl
```

設計上のリーク分離:

```text
pre_entry_context:
  シグナル品質評価用

post_entry_context:
  結果説明用

post-entryを使ってentry前理由を作らない。
```

一行コマンド例:

```bat
python scripts\build_trade_feature_snapshots.py --trade-outcome-csv data\runtime_logs\trade_ai_review\trade_outcome_ledger.csv --m15-csv "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\goldsharp_m15.csv" --m5-csv "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\goldsharp_m5.csv" --h1-csv "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\goldsharp_h1.csv" --h4-csv "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\goldsharp_h4.csv" --d1-csv "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\goldsharp_d1.csv" --output-csv data\runtime_logs\trade_ai_review\trade_feature_snapshot.csv --output-jsonl data\runtime_logs\trade_ai_review\trade_feature_snapshot.jsonl --output-json data\runtime_logs\trade_ai_review\trade_feature_snapshot_summary.json
```

注意:

```text
現時点のコマンド例はGOLD用CSV名を仮定。
BTCも評価する場合は、BTC用CSVを別途指定する運用にするか、symbol別にsnapshotを分ける追加対応が必要。
```

---

### Step 4: AI review payload作成

```text
scripts/build_trade_ai_review_payloads.py
```

役割:

```text
trade_feature_snapshot.jsonl を OpenAI APIに渡しやすいpayload JSONLへ整形する。
```

出力:

```text
trade_ai_review_payloads.jsonl
```

含めるもの:

```text
system_prompt
user_prompt
expected_response_schema
tag_taxonomy
review_contract
trade
compact_features
pre_entry_context
post_entry_context
```

プロンプト上の重要ルール:

```text
HYPOTHESIS_TAGGING_ONLY
DO_NOT_CHANGE_RULE_FROM_SINGLE_CASE
pre-entryとpost-entryを分ける
post-entryを使ってentry前の理由を作らない
JSONのみ返す
```

一行コマンド例:

```bat
python scripts\build_trade_ai_review_payloads.py --feature-snapshot-jsonl data\runtime_logs\trade_ai_review\trade_feature_snapshot.jsonl --output-jsonl data\runtime_logs\trade_ai_review\trade_ai_review_payloads.jsonl --output-json data\runtime_logs\trade_ai_review\trade_ai_review_payloads_summary.json
```

---

### Step 5: AIレビュー実行

```text
scripts/run_trade_ai_review_from_payloads.py
```

役割:

```text
trade_ai_review_payloads.jsonl を1件ずつOpenAI APIへ送り、trade_ai_review_ledger.jsonl に保存する。
```

安全仕様:

```text
should_change_strategy_from_this_single_trade は常に False に正規化する。
review_role は HYPOTHESIS_TAGGING_ONLY に固定する。
single_trade_warning は DO_NOT_CHANGE_RULE_FROM_SINGLE_CASE に固定する。
```

Dry-run例:

```bat
python scripts\run_trade_ai_review_from_payloads.py --payload-jsonl data\runtime_logs\trade_ai_review\trade_ai_review_payloads.jsonl --output-jsonl data\runtime_logs\trade_ai_review\trade_ai_review_ledger.jsonl --output-json data\runtime_logs\trade_ai_review\trade_ai_review_run_summary.json --dry-run --max-items 5
```

実API例:

```bat
python scripts\run_trade_ai_review_from_payloads.py --payload-jsonl data\runtime_logs\trade_ai_review\trade_ai_review_payloads.jsonl --output-jsonl data\runtime_logs\trade_ai_review\trade_ai_review_ledger.jsonl --output-json data\runtime_logs\trade_ai_review\trade_ai_review_run_summary.json --model gpt-5-mini --max-items 20
```

環境変数:

```text
OPENAI_API_KEY が必要。
OPENAI_MODEL を設定しておけば --model 省略時に使える。
```

---

### Step 6: タグ集計

```text
scripts/summarize_trade_ai_review_ledger.py
```

役割:

```text
trade_outcome_ledger.csv と trade_ai_review_ledger.jsonl を結合し、タグ別成績を出す。
```

出力:

```text
trade_ai_tag_summary.csv
trade_ai_tag_summary.json
```

集計項目:

```text
trade_count
win_count
loss_count
breakeven_count
win_rate
avg_r
total_r
profit_factor
max_losing_streak
tagged_vs_untagged_win_rate_diff
tagged_vs_untagged_avg_r_diff
overall_win_rate_diff
overall_avg_r_diff
tag_status
should_investigate
```

タグステータス:

```text
NEW:
  件数不足

WATCH:
  件数はあるが、数字上はまだ明確に悪くない

SUSPECT:
  件数があり、勝率差/平均R差/PFなどが悪い
```

現時点では `CONFIRMED` は自動付与しない。
`CONFIRMED` は後続の仮バックテスト検証で改善確認できたタグだけにする。

一行コマンド例:

```bat
python scripts\summarize_trade_ai_review_ledger.py --trade-outcome-csv data\runtime_logs\trade_ai_review\trade_outcome_ledger.csv --ai-review-jsonl data\runtime_logs\trade_ai_review\trade_ai_review_ledger.jsonl --output-csv data\runtime_logs\trade_ai_review\trade_ai_tag_summary.csv --output-json data\runtime_logs\trade_ai_review\trade_ai_tag_summary.json --min-sample 5
```

---

## 初回推奨実行順

まずはAIを呼ばずに dry-run まで確認する。

```text
1. export_mt5_closed_trade_history.py
2. build_trade_outcome_ledger_from_order_ledger.py
3. build_trade_feature_snapshots.py
4. build_trade_ai_review_payloads.py
5. run_trade_ai_review_from_payloads.py --dry-run --max-items 5
6. summarize_trade_ai_review_ledger.py
```

その後、payload内容とdry-run結果を確認してから、API実行する。

---

## 現時点の制限 / 次に確認すること

### 1. MT5履歴との結合精度

MT5履歴と既存order ledgerの列名・ticket保存状況により、結合精度が変わる。

確認ポイント:

```text
order ledger側に order_ticket / deal_ticket / position_ticket があるか
MT5履歴側の position_id と一致するか
送信ledgerの sent_at とMT5 entry_timeにズレがないか
symbol + direction + time近似で誤結合していないか
```

初回は `match_status` / `match_method` を必ず見る。

---

### 2. MFE/MAEは現時点ではM5 pathからの補助計算

`build_trade_outcome_ledger_from_order_ledger.py` ではMFE/MAEは未確定扱い。
`build_trade_feature_snapshots.py` 側でM5 pathから以下を出す。

```text
m5_mfe_points
m5_mae_points
m5_mfe_r
m5_mae_r
m5_first_touch_outcome
```

今後、outcome ledger側にもMFE/MAEを戻し込む統合を追加してよい。

---

### 3. GOLD/BTC混在snapshot

現時点の `build_trade_feature_snapshots.py` は、コマンドで指定したCSVを全トレードに使う。
GOLD/BTCを同一outcome ledgerに混ぜる場合、symbol別に分けて実行するか、将来的に以下を追加する。

```text
--m15-csv-gold
--m15-csv-btc
--h1-csv-gold
--h1-csv-btc
...
```

初期運用では、GOLDとBTCを分けてsnapshot作成するのが安全。

---

### 4. OpenAI SDK互換

`run_trade_ai_review_from_payloads.py` は `openai` Python SDK の Chat Completions 形式を使用している。
環境のSDKバージョンにより、レスポンス形式やモデル対応で修正が必要になる可能性がある。

まずは以下で確認する。

```bat
python scripts\run_trade_ai_review_from_payloads.py --payload-jsonl data\runtime_logs\trade_ai_review\trade_ai_review_payloads.jsonl --output-jsonl data\runtime_logs\trade_ai_review\trade_ai_review_ledger.jsonl --dry-run --max-items 1
```

その後、API実行を少量で試す。

---

### 5. Discord警告連携は未実装

現時点では、タグ集計CSVを作るところまで。
Discord通知へ以下のような警告を載せる処理は次ステップ。

```text
AI履歴警告:
- entry_after_extended_move: 過去12件 / 勝率33% / 平均R -0.41 / status=SUSPECT
```

既存通知に入れる場合も、最初は売買停止ではなく注意表示のみ。

---

## 禁止事項

```text
trade_ai_tag_summary.csv のSUSPECTだけで自動売買を止めない。
AIレビュー1件だけで戦略条件を変更しない。
負けトレードだけを集計して危険タグと断定しない。
post-entry情報をentry前の根拠にしない。
execution_issueをsignal_quality_issueとして扱わない。
```

---

## 次の実装候補

```text
1. GOLD/BTC symbol別 feature snapshot runner
2. outcome ledger と feature snapshot のMFE/MAE統合
3. タグsummaryをDiscord通知へ読み込む警告hook
4. SUSPECTタグの仮フィルタ検証スクリプト
5. human_review_note / human_override_tags を編集しやすいCSV補助ツール
```
