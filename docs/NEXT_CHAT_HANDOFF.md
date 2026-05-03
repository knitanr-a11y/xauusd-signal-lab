# NEXT CHAT HANDOFF

このドキュメントは、新しいチャットへ移行した直後に必ず読むこと。

## 最初に読むGitHub上の注意事項

新しいチャットでは、作業開始前に必ず以下を読む。

```text
docs/NEXT_CHAT_HANDOFF.md
docs/IMPORTANT_BTC_SPREAD_REVALIDATION.md
```

特にBTCについては、`docs/IMPORTANT_BTC_SPREAD_REVALIDATION.md` を読まずに通知・検証・採用判断を進めてはいけない。

## 現在の全体方針

MT5 + Pythonで、GOLD/XAUUSD・BTCUSD用のトレードシグナル検証/通知ツールを作成中。

GitHubリポジトリ：

```text
knitanr-a11y/xauusd-signal-lab
```

最終構成：

```text
MT5 / MQL5側:
- ローソク足取得
- 確定足をCSV出力

Python側:
- CSV読込
- シグナル判定
- payload生成
- AI評価
- Discord通知
- ledgerで再通知防止
```

PythonからMT5 APIでローソク足取得する方針ではない。

## MT5 CSVの場所

MQL5で出力されたローソク足CSVは以下に生成される。

```text
C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files
```

主なCSV：

```text
goldsharp_m15.csv
goldsharp_h1.csv
btcusdsharp_m5.csv
btcusdsharp_m15.csv
btcusdsharp_h1.csv
btcusdsharp_h4.csv
```

## BTCの最新状態

BTCは一度、スプレッド考慮不足でM5追加ルールを過大評価しかけた。
そのため、BTCは必ずCSVの `spread` 列を考慮して扱う。

詳しくは必ず以下を読む。

```text
docs/IMPORTANT_BTC_SPREAD_REVALIDATION.md
```

### BTC採用候補

```text
1. BTC_RUNNER_RR2_RISK1
   - スプレッド込みでも採用候補維持

2. BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8
   - 無条件通知は禁止
   - CSV最頻スプレッド + 値幅フィルタ通過時のみ通知・採用候補
```

BTC M5の必須値幅フィルタ：

```text
net_tp_after_spread_pips >= 5.0
spread_to_sl_ratio < 0.50
effective_rr_after_spread >= 1.0
```

現在のBTC本番通知候補スクリプト：

```text
scripts/run_live_btc_mtf_spread_filtered_notifier_from_csv.py
```

旧BTC通知スクリプトは本番では使わない。

```text
scripts/run_live_btc_mtf_notifier_from_csv.py
```

## BTCで完了済みの主な作業

```text
- M5/M15/H1/H4 CSV読込
- BTC RUNNER検出
- BTC M5追加ルール検出
- CSV spread列の最頻値採用
- 実質TP幅 / spread-to-SL / 実質RR フィルタ
- 小幅シグナルの通知除外
- Discord通知文整備
- AI評価接続
- ledger再通知防止
- スプレッド込み再検証
- 値幅フィルタ後の採用候補集計
```

確認済みの小幅シグナル例：

```text
2026-05-03 14:05 BTC BUY
net_tp_after_spread_pips = 2.99
spread_to_sl_ratio = 85.9%
effective_rr_after_spread = 0.61
```

これは検出されても通知しない。

## GOLDの最新状態

GOLD通知スクリプトを追加済み。

```text
scripts/run_live_gold_notifier_from_csv.py
```

対応済み：

```text
- MQL5 Files直下CSVのlive形式読み込み
- GOLD ABC v3検出
- GOLD EXTRA HIGH検出
- GOLD EXTRA STANDARD検出
- GOLD_COUNTER_BUY_ONLYを本番通知から除外
- regime guard表示整理
- TP/SL価格目安表示
- Discord通知文生成
- AI評価接続
- ledger再通知防止
```

GOLD本番採用ラベル：

```text
GOLD_ABC_V3
GOLD_EXTRA_HIGH_RSI_STOCH
GOLD_EXTRA_BB_BALANCE
```

本番除外ラベル：

```text
GOLD_COUNTER_BUY_ONLY
```

`GOLD_COUNTER_BUY_ONLY` は `--include-excluded` を付けたデバッグ時のみ表示可能。

## GOLD regime guardの扱い

GOLD ABC BUY danger regime は以下だけ対象。

```text
strategy_label == GOLD_ABC_V3
side == BUY
```

GOLD EXTRAやSELLでは対象外。
通知では以下のように表示する。

```text
regime guard: 対象外（GOLD ABC BUYのみ判定）
```

GOLD ABC BUYでdanger trueの場合だけ警戒表示にする。

```text
⚠️ GOLD ABC BUY danger regime: TRUE
扱い: 警戒通知のみ / AI評価必須 / ロット低下候補
```

## GOLD AI評価の最新修正

GOLDのAI評価は、OpenAIの自由文が不安定だった。
以下の問題が出た。

```text
- 54トレードなど存在しない数字が出る
- GOLD ABC BUY danger regime falseを理由に混ぜる
- 履歴不足・市場環境不透明などpayload外の曖昧表現が出る
```

そのため、`scripts/ai_signal_review.py` でGOLDは戦略別の定型評価で上書きするよう修正済み。

GOLD AI評価に使う固定実績：

```text
GOLD ABC v3:
216件 / 勝率59.26% / +104.0R / PF2.18

GOLD EXTRA HIGH:
44件 / 勝率70.45% / +28.1R / PF3.16 / 最大連敗2

GOLD EXTRA STANDARD:
17件 / 勝率52.94% / +5.5R / PF1.69
```

次のチャットでは、この修正後にもう一度GOLD dry-runを実行して確認する。

## 直近で最後に行った修正

最後に行った修正：

```text
scripts/ai_signal_review.py
```

コミット：

```text
27ba51d3c59965aff6724f154ef03d02778c4679
```

目的：

```text
GOLDのAI評価を戦略別の定型レビューで安定化する
```

次のチャットでは、まずGitHub Desktopで `Fetch origin` → `Pull origin` して、この修正を取り込む。

## 次にやること

### 1. GOLD dry-runを再確認

まず以下を実行する。

```bat
python scripts/run_live_gold_notifier_from_csv.py --m15-csv "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\goldsharp_m15.csv" --h1-csv "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\goldsharp_h1.csv" --history-csv data/results/gold_btc_final_portfolio_trades.csv --scan-recent-bars 3000 --enable-ai-review --dry-run --ledger-csv data/results/live_payloads/test_gold_notifier_ledger_5.csv
```

確認ポイント：

```text
- Rows: 30000 付近になること
- GOLD_COUNTER_BUY_ONLY がRejected excluded signalsに出ること
- 通知候補には採用ラベルだけ出ること
- regime guardがGOLD EXTRA/SELLでは対象外になること
- AI評価に54件など誤った数字が出ないこと
- AI評価にdanger regime falseを理由として出さないこと
- AI評価が戦略別実績ベースになること
```

### 2. GOLD本番運用用のscan範囲を60にする

デバッグでは `--scan-recent-bars 3000` を使って過去シグナルを確認した。
本番では過去シグナルが大量に出るため、まずは以下を基本にする。

```text
--scan-recent-bars 60
```

M15の60本なので約15時間分。

### 3. GOLD実送信テスト

dry-runが問題なければ、GOLDをDiscordへ実送信する。

```bat
python scripts/run_live_gold_notifier_from_csv.py --m15-csv "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\goldsharp_m15.csv" --h1-csv "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\goldsharp_h1.csv" --history-csv data/results/gold_btc_final_portfolio_trades.csv --scan-recent-bars 60 --enable-ai-review --send-discord
```

`.env` には以下が必要。

```env
DISCORD_WEBHOOK_URL=...
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
```

### 4. GOLD/BTC統合ライブ通知へ進む

GOLDとBTCの個別通知が問題なければ、次は統合スクリプトを作る。

候補：

```text
scripts/run_live_portfolio_notifier_from_csv.py
```

役割：

```text
- GOLD通知スクリプトを呼ぶ/同等処理を実行
- BTC spread_filtered通知スクリプトを呼ぶ/同等処理を実行
- 1回の実行でGOLD/BTC両方を確認
- それぞれのledgerで再通知防止
- Discordへ必要な通知だけ送る
```

## 次のチャットで絶対に避けること

```text
- docs/IMPORTANT_BTC_SPREAD_REVALIDATION.md を読まずにBTCを触る
- BTCでスプレッドなしの理論RRだけを見る
- BTC本番通知に旧スクリプトを使う
- GOLD_COUNTER_BUY_ONLYを本番通知に戻す
- GOLD EXTRA/SELLでdanger regimeを理由にする
- AI自由文を無条件に信用する
```

## 現在のおすすめ次ステップ

次のチャットでは、まず以下の順番で進める。

```text
1. docs/NEXT_CHAT_HANDOFF.md を読む
2. docs/IMPORTANT_BTC_SPREAD_REVALIDATION.md を読む
3. GitHub Desktopで Fetch origin → Pull origin
4. GOLD dry-run ledger_5 を実行
5. GOLD AI評価が定型レビューになったか確認
6. 問題なければ GOLD実送信テスト
7. その後、GOLD/BTC統合ライブ通知スクリプト作成
```
