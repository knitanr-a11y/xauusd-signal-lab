# NEXT CHAT HANDOFF

このドキュメントは、新しいチャットへ移行した直後に必ず読むこと。

## 最初に読むGitHub上の注意事項

新しいチャットでは、作業開始前に必ず以下を読む。

```text
docs/NEXT_CHAT_HANDOFF.md
docs/IMPORTANT_BTC_SPREAD_REVALIDATION.md
```

特にBTCについては、`docs/IMPORTANT_BTC_SPREAD_REVALIDATION.md` を読まずに通知・検証・採用判断を進めてはいけない。

## 最重要：本番ループ起動コマンド

通常運用で起動するコマンドはこれ。

```bat
scripts\run_live_portfolio_notifier_loop.bat
```

停止する場合：

```text
Ctrl + C
Y
```

起動後に見るポイント：

```text
Timing: every minute at xx:01
Bar offset: 0 (MQL5 CSV confirmed bars only)
Run started: xx:xx:01.xx
GOLD: OK returncode=0
BTC: OK returncode=0
```

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
- 確定足のみCSV出力
- Pythonが読みやすいMQL5\Files配下へ保存

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

## MQL5 CSV Export EA

現在のEA：

```text
mql5/Experts/ExportOhlcToCsv.mq5
```

重要仕様：

```text
#property version "1.30"
InpIncludeCurrentBar = false
InpAlignExportToMinute = true
InpExportSecond = 0
InpTimerSeconds = 1
InpAppendMode = true
InpAppendLookbackBars = 20
```

意味：

```text
- 未確定足はCSVへ出さない
- CopyRates start_pos=1 で確定足だけ取得する
- 毎分00秒にCSV更新を寄せる
- Python側は毎分01秒にCSVを読む
- 起動時は指定本数ぶんCSVを全件作成
- 通常運用時は新しい確定足だけ追記
```

EA v1.30の追記モードはBTCで確認済み。

確認ログ：

```text
btcusdsharp_m5.csv:
rows=30002 -> 30003
last_time=2026.05.03 18:35:00 -> 2026.05.03 18:40:00
mtime_changed=True
rows_changed=True
last_time_changed=True

btcusdsharp_m15.csv:
rows=30000 -> 30001
last_time=2026.05.03 18:15:00 -> 2026.05.03 18:30:00
mtime_changed=True
rows_changed=True
last_time_changed=True

btcusdsharp_h1.csv / btcusdsharp_h4.csv:
確認時間内では未確定のため変化なし。正常。
```

MQL5側の初回出力本数：

```text
M5: 30000
M15: 30000
H1: 20000
H4: 10000
```

## bar-offset の重要仕様

MQL5 EA が確定足だけをCSVへ出すため、Python側は最新CSV行をそのまま使う。

```text
--bar-offset 0
```

`--bar-offset 1` は使わない。
`--bar-offset 1` にすると、M5なら5分前、M15なら15分前の足を見てしまう。

## 現在の本番ループ

本番ループ用bat：

```text
scripts/run_live_portfolio_notifier_loop.bat
```

現在の動き：

```text
Timing: every minute at xx:01
Bar offset: 0 (MQL5 CSV confirmed bars only)
```

起動コマンド：

```bat
scripts\run_live_portfolio_notifier_loop.bat
```

理想タイミング：

```text
毎分00秒: MQL5 EA v1.30 が確定足CSVを追記/必要時更新
毎分01秒: Python bat がCSVを読み、GOLD/BTCを判定して必要ならDiscord通知
```

## 統合ライブ通知スクリプト

統合スクリプト：

```text
scripts/run_live_portfolio_notifier_from_csv.py
```

役割：

```text
- GOLD通知スクリプトを呼ぶ
- BTC spread_filtered通知スクリプトを呼ぶ
- 1回の実行でGOLD/BTC両方を確認
- それぞれのledgerで再通知防止
- Discordへ必要な通知だけ送る
```

現在batから呼ばれる主な引数：

```text
--gold-scan-recent-bars 60
--btc-scan-recent-m5-bars 60
--btc-scan-recent-m15-bars 20
--bar-offset 0
--btc-spread-mode csv_mode
--btc-spread-source m5
--btc-point-size 0.01
--btc-pip-size 10
--enable-ai-review
--send-discord
```

## 直近の本番ループ確認結果

2026-05-04 00:16〜00:17 JST付近のログで確認済み。

確認済み：

```text
Timing: every minute at xx:01
Run started: 00:16:01.05
Run finished: 00:16:05.45
Run started: 00:17:01.05
Run finished: 00:17:05.35
GOLD: OK returncode=0
BTC: OK returncode=0
```

つまり、統合処理全体は約4秒台まで短縮済み。

## 軽量化の最新状態

MQL5の元CSVは大きいまま保持する。
Python側の通知スクリプト内部だけで、`data/results/live_payloads/_runtime_tail/` に一時CSVを作り、直近本数だけでインジケーター計算する。

GOLD軽量化：

```text
scripts/run_live_gold_notifier_from_csv.py
M15: 3000 / 30000
H1: 1500 / 20000
```

BTC軽量化：

```text
scripts/run_live_btc_mtf_spread_filtered_notifier_from_csv.py
M5: 3000 / 30000
M15: 1500 / 30000
H1: 1000 / 20000
H4: 500 / 10000
```

ログ確認例：

```text
GOLD:
Rows: 3000
Runtime context rows: M15 3000/30000 H1 1500/20000

BTC:
Rows: M5 3000 M15 1500
Runtime context rows: M5 3000/30000 M15 1500/30000 H1 1000/20000 H4 500/10000
```

## GOLDの最新状態

GOLD通知スクリプト：

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
- runtime tail CSVによる軽量化
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

## GOLD AI評価の最新状態

GOLDのAI評価は、OpenAIの自由文が不安定だったため、`scripts/ai_signal_review.py` でGOLDは戦略別の定型評価で上書きするよう修正済み。

GOLD AI評価に使う固定実績：

```text
GOLD ABC v3:
216件 / 勝率59.26% / +104.0R / PF2.18

GOLD EXTRA HIGH:
44件 / 勝率70.45% / +28.1R / PF3.16 / 最大連敗2

GOLD EXTRA STANDARD:
17件 / 勝率52.94% / +5.5R / PF1.69
```

## BTCの最新状態

BTCは一度、スプレッド考慮不足でM5追加ルールを過大評価しかけた。
そのため、BTCは必ずCSVの `spread` 列を考慮して扱う。

詳しくは必ず以下を読む。

```text
docs/IMPORTANT_BTC_SPREAD_REVALIDATION.md
```

BTC本番通知スクリプト：

```text
scripts/run_live_btc_mtf_spread_filtered_notifier_from_csv.py
```

旧BTC通知スクリプトは本番では使わない。

```text
scripts/run_live_btc_mtf_notifier_from_csv.py
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

確認済みの小幅シグナル例：

```text
2026-05-03 14:05 BTC BUY
net_tp_after_spread_pips = 2.99
spread_to_sl_ratio = 85.9%
effective_rr_after_spread = 0.61
```

これは検出されても通知しない。
直近ログでもこのシグナルは検出され、値幅フィルタで正しく除外されている。

## Discord / OpenAI env

`.env` には以下が必要。

```env
DISCORD_WEBHOOK_URL=...
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
```

`--enable-ai-review` を付けているため、OpenAI APIキーが必要。

## 直近の重要コミット

```text
f0056d40690dbb413b0db67cfff51fcd276df79b
- MQL5 CSV Export EAをv1.30へ更新。起動時全件作成 + 通常時追記モード。

ca258317b23f74e0a5fa05d3d9ae802b0ae04c46
- BTC CSV出力確認用スクリプト追加。

4724cd279afe80b58ca997043f8bb8b1734fb22c
- MQL5 CSV Export EAを毎分00秒寄せに変更（v1.20時点）

bbf407fea142c54f96c1010ce8eb6a54ff8f80e2
- Python本番batを毎分01秒起動に変更

2653f25a9ce37e1e6d6fcf2728fbca4e20b52335
- BTC live通知のruntime tail軽量化

82c066ce0ed59f88a3cf0522ae8082997df67088
- GOLD live通知のruntime tail軽量化
```

## 次にやること

次回はAI評価の続きから進める。

```text
1. docs/NEXT_CHAT_HANDOFF.md を読む
2. docs/IMPORTANT_BTC_SPREAD_REVALIDATION.md を読む
3. GitHub Desktopで Fetch origin → Pull origin
4. 本番ループを起動する場合は scripts\run_live_portfolio_notifier_loop.bat
5. AI評価はBTC側の定型評価追加から進める
```

AI評価の現状：

```text
GOLD:
- 定型評価済み
- 戦略別固定実績で上書き

BTC:
- rule_profilesはある
- acceptedになった通知対象だけOpenAI評価される
- GOLDのような btc_deterministic_review() は未実装
```

次回のAI評価タスク：

```text
scripts/ai_signal_review.py に btc_deterministic_review() を追加する。

BTC_RUNNER_RR2_RISK1:
- スプレッド込みでも採用候補
- 77件 / 勝率61.04% / +64.0R / PF3.13 / 平均実質RR1.68
- 通常〜慎重

BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8:
- 値幅フィルタ通過時のみ評価対象
- 109件 / 勝率64.22% / +101.0R / PF3.59
- M5短期なので慎重寄り
```

今後の改善候補：

```text
- FutureWarningの解消
- CSV読み込み中衝突に備えたリトライ処理
- Discord通知が実際に出たときのledger確認
- AI評価APIの失敗時フォールバック強化
```

## 次のチャットで絶対に避けること

```text
- docs/IMPORTANT_BTC_SPREAD_REVALIDATION.md を読まずにBTCを触る
- BTCでスプレッドなしの理論RRだけを見る
- BTC本番通知に旧スクリプトを使う
- GOLD_COUNTER_BUY_ONLYを本番通知に戻す
- GOLD EXTRA/SELLでdanger regimeを理由にする
- --bar-offset 1 に戻す
- MQL5 EAが未確定足を出している前提で話を進める
- AI自由文を無条件に信用する
```
