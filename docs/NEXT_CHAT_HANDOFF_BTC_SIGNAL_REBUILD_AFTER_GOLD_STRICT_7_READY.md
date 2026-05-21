# NEXT_CHAT_HANDOFF_BTC_SIGNAL_REBUILD_AFTER_GOLD_STRICT_7_READY

Last updated: 2026-05-21

この文書は、BTC strict 5 再構築後の現状を次チャットへ引き継ぐためのメモです。

---

## 1. 最初に読むこと

新チャットでは、まず以下を読むこと。

```text
docs/NEXT_CHAT_HANDOFF_BTC_SIGNAL_REBUILD_AFTER_GOLD_STRICT_7_READY.md
docs/NEXT_CHAT_HANDOFF_GOLD_STRICT_7_LIVE_READY.md
docs/GOLD_STRICT_7_BACKTEST_AI_REVIEW_INITIAL_RESULT.md
```

---

## 2. 現在の結論

BTC側は、既存BTCシグナルを捨て、未来情報なし・確定足のみ・スプレッド込みで strict 5 として再構築済み。

現時点では、以下まで実装・接続済み。

```text
- BTC strict 5 候補探索
- M15/H1/H4 確定足のみの context join
- D1不使用
- スプレッド込みバックテスト
- official filter variant 固定
- Discord通知
- guarded demo send
- 毎分02秒 aligned loop
- 通知時 numeric AI tag 推定
- トレード後AI評価wrapper
```

BTC側は、仕組みとしては一旦完了。残る確認は、実際に自動売買BATで注文ledgerが作られた後、トレード後AI評価BATが通るかどうか。

---

## 3. official variant

BTC strict 5 の公式variantは以下で固定。

```text
buy_h4_context_conservative_v1
```

baseline は比較用として残っているが、通常運用では使わない。

このvariantでは、BUY CCI / BUY RSI40 の H4逆行系に対して conservative filter を適用済み。

重要:

```text
- H1/H4は確定足のみ
- D1は使わない
- 最新CSV行は確定足前提
- 形成中足、未来足は使わない
```

---

## 4. BTC strict 5 主要スクリプト

### official preview / runtime

```text
scripts/btc_strict_5_signals/run_btc_strict_5_official_preview_from_csv.py
scripts/btc_strict_5_signals/btc_strict_5_official_runtime.py
scripts/btc_strict_5_signals/btc_strict_5_filter_variants.py
```

### official Discord通知

通常運用で使う通知BAT:

```text
scripts/run_btc_strict_5_official_discord_numeric_ai_tags_forever_aligned_weekly_state.bat
```

通知loop本体:

```text
scripts/run_btc_strict_5_official_discord_numeric_ai_tags_forever_aligned_weekly_state.py
```

単発通知テスト用:

```text
scripts/run_btc_strict_5_official_discord_notifier_with_numeric_ai_tags_from_csv.bat
scripts/btc_strict_5_signals/run_btc_strict_5_official_discord_notifier_with_numeric_ai_tags_from_csv.py
```

古い通知BATやbaseline系は通常運用では使わない。

### guarded demo send

通常運用で使う自動売買BAT:

```text
scripts/run_btc_strict_5_official_guarded_demo_send_forever_aligned_weekly_state.bat
```

これを起動しない限り、BTC strict 5 official の order ledger は作られない。

### トレード後AI評価

```text
scripts/run_btc_strict_5_official_ai_review_pipeline.bat
scripts/run_btc_strict_5_official_ai_review_pipeline.py
```

order ledger がまだ無い場合は、エラーではなく以下で安全終了する。

```text
status: NO_ORDER_LEDGER_YET
cycle_ok: true
ai_called: false
mt5_history_export_called: false
```

---

## 5. 普段起動するBTC BAT

BTCの通常運用では、通知と自動売買を別々のコマンドプロンプトで起動する。

### 通知

```text
scripts/run_btc_strict_5_official_discord_numeric_ai_tags_forever_aligned_weekly_state.bat
```

内容:

```text
毎分02秒
Discord通知
official conservative_v1
numeric AI tag 推定あり
重複通知はledgerで防止
OpenAI呼び出しなし
MT5発注なし
D1不使用
```

### 自動売買

```text
scripts/run_btc_strict_5_official_guarded_demo_send_forever_aligned_weekly_state.bat
```

内容:

```text
毎分02秒
official conservative_v1
guarded demo send
発注あり
position guardあり
order ledger作成あり
```

### トレード後AI評価

実際に発注・決済が発生した後に実行する。

```text
scripts/run_btc_strict_5_official_ai_review_pipeline.bat
```

---

## 6. BTC runtime ledger / 出力先

通知ledger:

```text
data/runtime_state/btc/strict_5/official_discord_numeric_ai_tag_ledger.csv
```

autotrade order ledger:

```text
data/runtime_state/btc/strict_5/official_guarded_demo_order_ledger.csv
```

AI tag numeric rules:

```text
data/runtime_state/btc/strict_5/ai_tag_numeric_rules.json
data/runtime_state/btc/strict_5/ai_tag_numeric_rules_summary.csv
```

post-trade AI review 出力:

```text
data/runtime_logs/trade_ai_review_btc_strict_5_official/
```

主なsummary:

```text
data/runtime_logs/trade_ai_review_btc_strict_5_official/btc_strict_5_official_ai_review_pipeline_summary.json
data/runtime_logs/trade_ai_review_btc_strict_5_official/btc_ai_review_pipeline_same_spec_summary.json
data/runtime_logs/trade_ai_review_btc_strict_5_official/trade_ai_tag_summary.csv
```

---

## 7. 通知時 numeric AI tag 推定

通知時にはOpenAIを呼ばない。

過去のpost-trade AI評価から作った数値ルールを読み、現在シグナルにHITしたタグだけを表示する。

```text
過去AI評価
  -> numeric rule JSON
  -> 通知時に現在シグナルへ適用
  -> HITしたタグだけDiscordへ表示
```

ルール生成BAT:

```text
scripts/build_btc_strict_5_ai_tag_numeric_rules.bat
```

このBATは、numeric condition diagnostics を再構築し、`ai_tag_numeric_rules.json` を作る。

通知BATは、ルールJSONが無ければ自動生成を試みる。

通知例:

```text
AIタグ推定:
個別AIタグ推定: なし
AIタグ数値ルール: checked=9 hit=0
個別AI判定: 未実施（OpenAIは呼ばない）
```

HIT時:

```text
AIタグ推定:
個別AIタグ推定: ⚠️ HIT 1件
- high_volatility_chase / WATCH / WARN
  根拠: ...
```

重要:

```text
checked=N hit=0 は、N個のルールを確認し、今回は警告なしという意味。
hit>0 の場合のみ、その個別シグナルに警告タグ推定が付く。
```

---

## 8. BTC AI tag numeric rules の現在地

最終確認時点では以下まで確認済み。

```text
rules_count: 31
ai_tag_rules_cycle_ok: true
Donch96: checked=9 hit=0
Donch32: checked=6 hit=0
```

つまり、ルールJSONの読み込みNG問題は解消済み。

今回確認した2件では、AIタグ数値ルールは確認されたがHITなし。

---

## 9. トレード後AI評価BAT

追加済み:

```text
scripts/run_btc_strict_5_official_ai_review_pipeline.bat
scripts/run_btc_strict_5_official_ai_review_pipeline.py
```

対象order ledger:

```text
data/runtime_state/btc/strict_5/official_guarded_demo_order_ledger.csv
```

このledgerは、通知BATではなく自動売買BATが作る。

まだ注文ledgerが無い状態で実行すると、以下で正常スキップする。

```text
status: NO_ORDER_LEDGER_YET
cycle_ok: true
ai_called: false
orders_sent: false
```

実際にBTC strict 5 officialの注文が発生し、決済済みトレードが出てから再実行する。

---

## 10. BTCの次に確認すること

次にBTCで確認すべきこと:

```text
1. 通知BATを起動し続ける
2. 自動売買BATを別窓で起動し続ける
3. official_guarded_demo_order_ledger.csv が作られるか確認
4. 決済後、run_btc_strict_5_official_ai_review_pipeline.bat を実行
5. trade_ai_review_btc_strict_5_official 出力を確認
6. 2回目実行で評価済みがスキップされるか確認
```

BTCは、実装追加ではなく実運用確認フェーズ。

---

## 11. 注意事項

```text
- 既存BTC multi_strategy のledgerとは混ぜない。
- BTC strict 5 official のruntime_stateだけを見る。
- 通知BATだけではorder ledgerは作られない。
- 自動売買BATを起動して初めて official_guarded_demo_order_ledger.csv ができる。
- トレード後AI評価は、通知時AIタグ推定とは別物。
```

---

## 12. このチャットで追加・更新した主なファイル

```text
scripts/ai_tag_numeric_rule_utils.py
scripts/btc_strict_5_signals/build_btc_strict_5_ai_tag_numeric_rules.py
scripts/build_btc_strict_5_ai_tag_numeric_rules.bat
scripts/btc_strict_5_signals/run_btc_strict_5_official_discord_notifier_with_numeric_ai_tags_from_csv.py
scripts/run_btc_strict_5_official_discord_notifier_with_numeric_ai_tags_from_csv.bat
scripts/run_btc_strict_5_official_discord_numeric_ai_tags_forever_aligned_weekly_state.py
scripts/run_btc_strict_5_official_discord_numeric_ai_tags_forever_aligned_weekly_state.bat
scripts/run_btc_strict_5_official_ai_review_pipeline.py
scripts/run_btc_strict_5_official_ai_review_pipeline.bat
```

---

## 13. 次チャット開始時の推奨確認

次チャットでは、ユーザーが以下を貼ったらこの文書から再開する。

```text
BTC strict 5 と GOLD strict 7 の続きです。
まず docs/NEXT_CHAT_HANDOFF_BTC_SIGNAL_REBUILD_AFTER_GOLD_STRICT_7_READY.md と docs/NEXT_CHAT_HANDOFF_GOLD_STRICT_7_LIVE_READY.md を読んでください。
```

BTC側で最初に見るべきもの:

```text
data/runtime_state/btc/strict_5/official_discord_numeric_ai_tag_ledger.csv
data/runtime_state/btc/strict_5/official_guarded_demo_order_ledger.csv
data/runtime_logs/trade_ai_review_btc_strict_5_official/btc_strict_5_official_ai_review_pipeline_summary.json
```
