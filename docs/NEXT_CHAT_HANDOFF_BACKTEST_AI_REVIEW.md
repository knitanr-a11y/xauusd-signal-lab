# NEXT CHAT HANDOFF - Backtest AI Review

## 目的

次チャットでは、ライブAI評価パイプラインの次段階として **バックテスト結果をAI評価に入れる仕組み** を実装する。

目的は、ライブ実績を置き換えることではない。ライブ実績は最重要・最高信頼の履歴として残し、バックテストAI評価は「サンプル不足を補う補助情報」として使う。

次チャットでやることは、まず BTC の `D1_LOW_BREAK_SELL` を対象に、バックテスト trades.csv から live-compatible な `trade_outcome_ledger.csv` を作り、既存のAIレビュー基盤に通すこと。

---

## 現在のライブ稼働フロー

### 1. もちぽよGOLD

BAT:

```text
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned_weekly_logs.bat
```

もちぽよGOLDは既存のDiscord送信経路にAI履歴警告が接続済み。

### 2. GOLD multi-strategy

推奨BAT:

```text
scripts/run_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state_ai_discord.bat
```

同時起動禁止の旧/補助BAT:

```text
scripts/run_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state.bat
scripts/run_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state_ai_marker.bat
```

固定order ledger:

```text
data/runtime_state/gold/multi_strategy/guarded_demo_order_ledger.csv
```

multi AI Discord ledger:

```text
data/runtime_state/gold/multi_strategy/multi_ai_history_discord_send_ledger.csv
```

### 3. BTC multi-strategy

BAT:

```text
scripts/run_btc_multi_strategy_guarded_demo_send_forever_aligned_weekly_state.bat
```

固定order ledger:

```text
data/runtime_state/btc/multi_strategy/guarded_demo_order_ledger.csv
```

BTC once wrapper は、Discord signal notification が `SENT` になってからMT5送信する安全ゲート設計。

---

## ライブAI評価の現在地

### GOLDライブAI評価

実行BAT:

```text
scripts/run_gold_ai_review_pipeline_mochipoyo_and_multi.bat
```

主な出力:

```text
data/runtime_logs/trade_ai_review/gold_ai_review_pipeline_summary.json
data/runtime_logs/trade_ai_review/trade_ai_tag_summary.json
data/runtime_logs/trade_ai_review/trade_ai_tag_summary.csv
```

直近の確認結果:

```text
cycle_ok: true
outcome_rows: 11
outcome_matched_rows: 10
outcome_unmatched_rows: 1
feature_snapshot_rows: 11
review_rows_written: 11
review_error_rows: 0
tag_summary_rows: 25
should_investigate_rows: 0
```

現時点で正式な停止・条件変更対象はない。

ただし、GOLDで観察継続すべきタグ:

```text
GOLD_H4_M15_DAYTRADE:
- ema_distance_too_large
- entry_after_extended_move
- m15_signal_candle_large
- high_volatility_chase
- poor_pullback_structure
- macd_late_signal

GOLD_H4_M5_SCALP:
- entry_after_extended_move
- high_volatility_chase
- m15_signal_candle_large
```

解釈:

- GOLDはまだAI評価上の強制停止レベルではない。
- ただし、伸びた後に入る、EMAから離れている、大きいM15足、高ボラ追いかけ系の負け方が観察対象。
- `ema_distance_too_large` と `entry_after_extended_move` は特に要観察。

### BTCライブAI評価

実行BAT:

```text
scripts/run_btc_ai_review_pipeline.bat
```

このBATは現在、same-spec wrapper を呼ぶ。

主な出力:

```text
data/runtime_logs/trade_ai_review_btc/btc_ai_review_pipeline_same_spec_summary.json
data/runtime_logs/trade_ai_review_btc/trade_ai_tag_summary.json
data/runtime_logs/trade_ai_review_btc/trade_ai_tag_summary.csv
```

直近の same_spec 確認結果:

```text
cycle_ok: true
normalization.strategy_filled_rows: 4
normalization.strategies:
  - D1_LOW_BREAK_SELL
  - PULLBACK_REJECT_SELL
payload_rows_jsonl: 4
review_rows_jsonl: 4
review_rows_written: 4
review_error_rows: 0
```

BTCで観察継続すべきタグ:

```text
D1_LOW_BREAK_SELL:
- ema_distance_too_large
- m15_signal_candle_large
- near_recent_low
- range_edge_entry
```

解釈:

- BTCもまだ正式停止・条件変更対象ではない。
- ただし、SELLで下げた後・安値付近・レンジ端・大きいM15足の追いかけ負けが疑わしい。
- 特に `near_recent_low` と `range_edge_entry` は、BTCのボラ特性上かなり重要。

---

## AI評価の基本方針

この方針はバックテストAI評価でも絶対に維持する。

```text
AI評価は仮説タグ付けのみ。
1件の負けでルール変更しない。
M15前100本を見る。
M15後20本は結果説明用であり、エントリー可否判断に使わない。
M5/H1/H4/D1文脈は可能な限り使う。
min_sampleは現在5。
発注停止・発注ブロック・ロット変更はまだ実装しない。
```

既存プロンプト/レビュー契約は、以下の思想を持つ:

```text
HYPOTHESIS_TAGGING_ONLY
DO_NOT_CHANGE_RULE_FROM_SINGLE_CASE
```

ユーザーの意図:

```text
1件の負けを重く見ない。
似たような負け理由が何件もたまったら危険かも、という肌感覚をAI評価に反映したい。
```

---

## 必ず読む既存ファイル

次チャットで最初に読むこと。

```text
scripts/build_trade_outcome_ledger_from_order_ledger.py
scripts/build_trade_feature_snapshots.py
scripts/build_trade_ai_review_payloads.py
scripts/run_trade_ai_review_from_payloads.py
scripts/summarize_trade_ai_review_ledger.py
scripts/trade_ai_review_utils.py
scripts/export_mt5_closed_trade_history.py
```

ライブ統合パイプライン:

```text
scripts/run_gold_ai_review_pipeline_mochipoyo_and_multi.py
scripts/run_gold_ai_review_pipeline_mochipoyo_and_multi.bat
scripts/run_btc_ai_review_pipeline.py
scripts/run_btc_ai_review_pipeline_same_spec.py
scripts/run_btc_ai_review_pipeline.bat
```

BTC稼働側:

```text
scripts/run_btc_multi_strategy_guarded_demo_send_forever_aligned_weekly_state.bat
scripts/run_btc_multi_strategy_guarded_demo_send_forever_aligned_weekly_state.py
scripts/run_btc_multi_strategy_guarded_demo_send_once.py
```

GOLD multi稼働側:

```text
scripts/run_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state_ai_discord.bat
scripts/run_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state_ai_discord.py
scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.py
```

---

## バックテストAI評価を作る理由

ライブ件数はまだ少ない。GOLD/BTCとも `should_investigate_rows=0` で、正式な調査警告には至っていない。

ただし、怪しいタグはすでに出ている。

バックテストAI評価で確認したいこと:

```text
BTC D1_LOW_BREAK_SELL で、ema_distance_too_large / m15_signal_candle_large / near_recent_low / range_edge_entry が出る時、バックテストでも負けやすいのか。

GOLD_H4_M15_DAYTRADE で、entry_after_extended_move / ema_distance_too_large が出る時、バックテストでも優位性が薄いのか。
```

まずはBTCの `D1_LOW_BREAK_SELL` を優先する。

---

## バックテストAI評価の出力はライブと分ける

バックテスト結果をライブAI評価にそのまま混ぜない。

推奨出力先:

```text
data/runtime_logs/trade_ai_review_backtest_btc/
data/runtime_logs/trade_ai_review_backtest_gold/
```

ライブ出力先は上書きしない:

```text
data/runtime_logs/trade_ai_review/
data/runtime_logs/trade_ai_review_btc/
```

バックテストは補助情報。ライブ実績が最重要。

将来的には以下を分けて表示する:

```text
LIVE tag summary
BACKTEST tag summary
LIVE + BACKTEST overlay summary
```

Discord表示の理想例:

```text
AI履歴警告:
LIVE: D1_LOW_BREAK_SELL / near_recent_low = 3 trades, PF 0.0, min_sample未満
BACKTEST: same tag = 42 trades, PF 0.68
判定: 注意。安値圏ショート追いかけの可能性
```

---

## バックテストtrades.csvに必要な列

最低限:

```text
symbol
strategy_id
strategy_key
direction
entry_time
entry_price
sl_price
tp_price
exit_time
exit_price
outcome
profit_r
order_key or trade_id
```

あると良い列:

```text
signal_close_time
broker_symbol
rr
spread
spread_cost
exit_reason
holding_minutes
max_favorable
max_adverse
```

BTCは特に、スプレッド込みnet Rが重要。可能ならgrossではなくnet成績を使う。

---

## 実装予定スクリプト

まず作るべきもの:

```text
scripts/build_trade_outcome_ledger_from_backtest_trades.py
```

役割:

```text
backtest trades.csv
↓
live-compatible trade_outcome_ledger.csv
```

その後:

```text
scripts/run_btc_backtest_ai_review_pipeline.py
scripts/run_btc_backtest_ai_review_pipeline.bat
```

将来的に:

```text
scripts/run_gold_backtest_ai_review_pipeline.py
scripts/run_gold_backtest_ai_review_pipeline.bat
scripts/merge_live_and_backtest_ai_tag_summary.py
```

初回はBTCだけでよい。

---

## バックテストAI評価のサンプリング

最初から全件をAI評価しない。

推奨:

```text
負け: 多め、または全件
勝ち: 比較用に負けと同数程度
建値: 少数
```

例:

```text
負け100件
勝ち100件
建値30件
```

AIレビューはタグ付け、統計判断はsummarizerが行う。

---

## 実装時の注意

1. JSONL件数
   - JSONLをCSVとして数えない。
   - non-empty line countで数える。

2. strategy補完
   - 空の `strategy_id`, `strategy_key`, `pair_name` は集計を壊す。
   - BTC same_specでは order_key / payload_key から補完済み。
   - backtest tradesでも必ず strategy を保持/補完する。

3. symbol正規化
   - `GOLD#` などは grouping symbol として `GOLD`。
   - `BTCUSD#` などは grouping symbol として `BTC`。
   - broker_symbolは別で事実として残す。

4. ローソク足CSV名
   - GOLD: `goldsharp_m15.csv`, `goldsharp_m5.csv`, `goldsharp_h1.csv`, `goldsharp_h4.csv`, `goldsharp_d1.csv`
   - BTC: `btcusdsharp_m15.csv`, `btcusdsharp_m5.csv`, `btcusdsharp_h1.csv`, `btcusdsharp_h4.csv`, `btcusdsharp_d1.csv`

5. 期限切れ添付
   - 古いアップロードファイルは期限切れになっているものがある。
   - 必要なCSVは新チャットで再添付してもらう。

---

## 次チャット用の開始文

以下を新チャットに貼る。

```text
GitHubリポジトリ knitanr-a11y/xauusd-signal-lab の以下を最初に読んで、続きからお願いします。

必須:
docs/NEXT_CHAT_HANDOFF_BACKTEST_AI_REVIEW.md

既存AI評価パイプライン確認:
scripts/build_trade_outcome_ledger_from_order_ledger.py
scripts/build_trade_feature_snapshots.py
scripts/build_trade_ai_review_payloads.py
scripts/run_trade_ai_review_from_payloads.py
scripts/summarize_trade_ai_review_ledger.py
scripts/trade_ai_review_utils.py
scripts/run_gold_ai_review_pipeline_mochipoyo_and_multi.py
scripts/run_btc_ai_review_pipeline_same_spec.py

現在の状況:
- もちぽよGOLD、GOLD multi、BTC multi のライブAI評価パイプラインは動作済み。
- GOLDは scripts/run_gold_ai_review_pipeline_mochipoyo_and_multi.bat で、もちぽよGOLD + GOLD multiを評価する。
- BTCは scripts/run_btc_ai_review_pipeline.bat で、BTC multiの data/runtime_state/btc/multi_strategy/guarded_demo_order_ledger.csv を評価する。
- BTC same_spec summaryでは strategy_filled_rows=4、strategies=[D1_LOW_BREAK_SELL, PULLBACK_REJECT_SELL]、review_error_rows=0 まで確認済み。
- GOLD/BTCとも、現時点では should_investigate_rows=0。まだ停止や条件変更はしない。

重要方針:
- AI評価は仮説タグ付けのみ。
- 1件の負けでルール変更しない。
- M15前100本、後20本。後20本は結果説明用で、エントリー可否の判断材料にしない。
- live結果とbacktest結果は混ぜず、別summaryとして管理する。
- backtest AI評価は、ライブサンプル不足を補う補助情報として使う。
- 自動停止、発注ブロック、ロット変更は今回まだ実装しない。

次にやること:
バックテスト結果をAI評価に入れる仕組みを作りたいです。
まずはBTCの D1_LOW_BREAK_SELL を優先して、バックテストtrades.csvから live-compatible な trade_outcome_ledger.csv を作る scripts/build_trade_outcome_ledger_from_backtest_trades.py を設計・実装してください。
その後 scripts/run_btc_backtest_ai_review_pipeline.py を作り、data/runtime_logs/trade_ai_review_backtest_btc/ に liveとは別のAIレビュー結果を出すようにしてください。

特に確認したい仮説:
BTC D1_LOW_BREAK_SELL で、ema_distance_too_large / m15_signal_candle_large / near_recent_low / range_edge_entry が出る時、バックテストでも負けやすいのか。
```
