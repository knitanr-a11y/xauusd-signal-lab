# NEXT_CHAT_HANDOFF_BTC_SIGNAL_REBUILD_AFTER_GOLD_STRICT_7_READY

Last updated: 2026-05-20

この文書は、新チャットでBTCシグナル作成を再開するための引き継ぎです。

---

## 1. 最初に読むこと

新チャットでは、まず以下を読むこと。

```text
docs/NEXT_CHAT_HANDOFF_BTC_SIGNAL_REBUILD_AFTER_GOLD_STRICT_7_READY.md
docs/NEXT_CHAT_HANDOFF_GOLD_STRICT_7_LIVE_READY.md
docs/GOLD_STRICT_7_BACKTEST_AI_REVIEW_INITIAL_RESULT.md
```

GOLD側の現状確認が不要なら、BTC作成に直接進んでよい。

---

## 2. GOLD側の現在地

GOLDは strict 7 候補で、以下まで接続済み。

```text
- strict 7 シグナル検出
- Discord通知
- guarded demo connector
- post-trade live AI review
- backtest AI review と live AI review の分離
- EAのCSV書き出し遅延対策として毎分監視へ変更済み
```

GOLD側は、デモ運用を開始できる構成。

ただし、最終完成判定は、実シグナル1件について以下を確認してから。

```text
通知
  -> strict 7 connector ledger
  -> 決済
  -> live AI評価
  -> 2回目AI評価で同じIDがスキップされること
```

GOLD側の現行引き継ぎ:

```text
docs/NEXT_CHAT_HANDOFF_GOLD_STRICT_7_LIVE_READY.md
```

---

## 3. 次にやること

次はBTCのシグナルを作り直す。

重要:

```text
既存BTCシグナルをそのまま本命にしない。
未来情報混入の疑いを踏まえ、BTCは厳密条件で再探索する。
```

今回の目的は、BTC用の新しいシグナル候補を、GOLD strict 7 と同じように、後で以下へ接続できる形にすること。

```text
BTC strict signal candidates
  -> 厳密バックテスト
  -> Discord通知
  -> guarded demo connector
  -> post-trade live AI review
```

ただし、最初から通知・発注へ進まない。

まずはBTCのシグナル候補探索と厳密バックテストを優先する。

---

## 4. BTCで特に重要な方針

BTCはスプレッドが大きいので、短すぎる値幅は避ける。

ユーザー希望:

```text
BTCは50 pips以上の値幅を取れるところを探索する。
```

ただし、ここでいう pips / price distance の扱いは、ブローカー銘柄仕様に依存するため、実装前にCSV価格桁と既存BTC sender仕様を確認すること。

探索では、以下を重視する。

```text
- スプレッド込みで成立する値幅
- PF 2以上を目指す
- 月別の偏り確認
- 最大DD確認
- 取引回数が少なすぎないこと
- 2026年4月など、悪化月があれば理由を考察
```

---

## 5. 未来情報禁止ルール

BTCでは特に厳格に守る。

```text
- 上位足は確定済み情報だけ使う
- MTF joinは context_close_time <= base_close_time を厳守
- 形成中のH1/H4/D1を使わない
- 形成中のM15/M5も使わない
- confirmed-time join を使う
- current forming candle 情報を前提にしない
```

今回のBTC再探索では、既存の成績が良かったとしても、未来情報の疑いがあるものは本命扱いしない。

---

## 6. BTCのCSV想定

ユーザーが使っているMT5 Files配下のBTC CSVは、おそらく以下。

```text
btcusdsharp_m5.csv
btcusdsharp_m15.csv
btcusdsharp_h1.csv
btcusdsharp_h4.csv
btcusdsharp_d1.csv
```

新チャットでユーザーに必要なら、これらを貼ってもらう。

ただし、GitHub上の既存スクリプト・既存データ出力があれば、まずそれを確認する。

---

## 7. 既存BTC関連で確認すべきファイル

BTCの既存接続・AI評価・送信まわりを確認するなら以下。

```text
scripts/run_btc_ai_review_pipeline_same_spec.py
scripts/run_btc_ai_review_pipeline.bat
scripts/run_btc_manual_demo_order_send_smoke_test.py
scripts/run_btc_manual_demo_order_send_smoke_test_send_once.py
scripts/send_mt5_order_from_payload.py
```

既存BTC multiのruntime ledger:

```text
data/runtime_state/btc/multi_strategy/guarded_demo_order_ledger.csv
```

ただし、次のBTCシグナル作成では、既存BTC候補を前提にしすぎない。

---

## 8. 既存BTC AI評価の状況

以前のBTC same_spec summaryでは以下まで確認済み。

```text
strategy_filled_rows: 4
strategies: [D1_LOW_BREAK_SELL, PULLBACK_REJECT_SELL]
review_error_rows: 0
should_investigate_rows: 0
```

ただし、これは既存BTC live AI評価の話であり、新しいBTC候補の性能保証ではない。

---

## 9. BTC探索の進め方

推奨順序:

```text
1. BTC CSVの列・時刻・価格桁・期間を確認
2. confirmed-time join基盤を確認または新規作成
3. 既存BTC候補を棚卸しするが、本命扱いしない
4. 多角的に候補を探索する
5. 候補ごとに月別成績・PF・最大DD・連敗・件数を見る
6. スプレッド込みnet成績を必須にする
7. 良い候補があってもすぐ通知/発注へ進めない
8. 候補を数本に絞ってから、GOLD strict 7 と同様の候補管理へ進む
```

使ってよい指標例:

```text
- Donchian breakout / breakdown
- EMA trend
- MACD momentum
- RSI / Stoch
- Bollinger / Keltner
- ATR / volatility filter
- CCI
- pullback / reclaim / rejection
```

ただし、1候補に詰め込みすぎない。

```text
インジケーターは2〜3個程度を基本にする。
```

---

## 10. バックテスト判定方針

BTCはスプレッドが大きいため、必ずnet評価にする。

```text
- spread込み
- 手数料や実運用差があれば考慮
- first-touch判定を明確にする
- TP/SL到達順の曖昧さを保守的に扱う
- 月別成績を見る
- 最大DDと連敗を見る
```

候補が良く見えても、以下は必ず確認する。

```text
- トレード数が極端に少なくないか
- 1ヶ月だけで稼いでいないか
- 悪化月の理由
- 大きなボラ局面だけに依存していないか
- レンジで連敗しないか
```

---

## 11. BTC候補を作るときの注意

ユーザーは、勝手にシグナルを本実装へ進めることを望んでいない。

必ず段階を守る。

```text
探索
  -> 数値比較
  -> 月別確認
  -> 候補名と条件を言語化
  -> ユーザー確認
  -> その後にコード整理
```

勝手にDiscord通知や自動売買へ接続しない。

---

## 12. 次チャットでの開始文例

新チャットでは、ユーザーは以下を貼る想定。

```text
GitHubリポジトリ knitanr-a11y/xauusd-signal-lab の以下を最初に読んで、続きからお願いします。

必須:
docs/NEXT_CHAT_HANDOFF_BTC_SIGNAL_REBUILD_AFTER_GOLD_STRICT_7_READY.md
docs/NEXT_CHAT_HANDOFF_GOLD_STRICT_7_LIVE_READY.md
docs/GOLD_STRICT_7_BACKTEST_AI_REVIEW_INITIAL_RESULT.md

次にやること:
GOLD strict 7 は運用開始可能な状態まで進みました。
次はBTCのシグナルを、未来情報なし・確定足のみ・スプレッド込みで作り直したいです。
既存BTCシグナルは参考程度にし、D1_LOW_BREAK_SELL なども本命扱いせず、BTC用の候補を多角的に再探索してください。
BTCはスプレッドが大きいので、50pips以上の値幅を取れるところを優先してください。
まずはコード実装ではなく、既存ファイル確認・CSV仕様確認・探索方針の整理からお願いします。
```

---

## 13. 現時点の結論

GOLD側は、運用開始可能な状態として記録済み。

BTC側は、次チャットで以下から再開する。

```text
BTC strict signal rebuild
未来情報なし
確定足のみ
スプレッド込み
50pips以上の値幅優先
PF 2以上を目指す
すぐ通知/発注へ接続しない
```
