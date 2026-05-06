# NEXT CHAT HANDOFF

このドキュメントは、新しいチャットへ移行した直後に必ず読むこと。

## 2026-05-06 追記: もちぽよ式 GOLD minimal live dry loop の続き

直近チャットでは、白紙からの候補探索ではなく、もちぽよ式 GOLD minimal live flow の部品検証とdry loop化を進めた。

次チャットでその続きから始める場合は、まず以下を読むこと。

```text
docs/NEXT_CHAT_HANDOFF_MOCHIPOYO_MINIMAL_LIVE.md
docs/MOCHIPOYO_GOLD_MINIMAL_LIVE_ONCE_STABILITY.md
docs/MOCHIPOYO_MINIMAL_LEDGER_VALIDATION.md
docs/MOCHIPOYO_MINIMAL_RISK_NOTIFICATION_VALIDATION.md
docs/MOCHIPOYO_MINIMAL_SCANNER_VALIDATION_LOG.md
```

現在の到達点:

```text
GOLD candidate generation: PASS
GOLD risk enrich: PASS
GOLD notification eligibility: PASS
GOLD trigger window filter: PASS
GOLD ledger duplicate filter: PASS
GOLD Discord dry-run / no-row skip: PASS
GOLD pair trigger state: PASS
GOLD minimal live once stability: PASS
GOLD minimal live dry loop: PASS
```

まだDiscord実送信はしていない。
自動売買もしていない。

次にやることは A案。

```text
長めのdry loop:
  iterations = 12
  sleep_seconds = 15
  out-dir は短く data/ml_loop_run5 推奨
```

実行予定コマンド:

```cmd
python scripts\run_mochipoyo_gold_minimal_live_loop_dry.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\ml_loop_run5 --symbol GOLD --trigger-state-csv data\results\mochipoyo\minimal_trigger_test\gold_pair_trigger_state.csv --notification-ledger-csv data\results\mochipoyo\minimal_live_once_test\gold_notification_ledger.csv --iterations 12 --sleep-seconds 15 --commit-trigger-state --commit-ledger
```

注意:

```text
- Discord実送信へすぐ進まない
- 自動売買を入れない
- 既存の run_mochipoyo_live_notify_loop.py / run_mochipoyo_live_notify_loop_light.py は使わない
- trigger更新窓フィルターを無効化しない
- 長い out-dir を使わない
```

---

## 最重要結論：GOLD/BTCのシグナル候補は一旦すべて白紙

2026-05-06時点で、GOLD/BTCの既存採用候補はすべて白紙に戻す。

```text
GOLD_ABC_V3
GOLD_EXTRA_HIGH_RSI_STOCH
GOLD_EXTRA_BB_BALANCE
GOLD_COUNTER_BUY_ONLY
BTC_RUNNER_RR2_RISK1
BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8
```

上記を次チャットで「採用済み」「本命候補」「通知対象」として扱ってはいけない。

理由：

```text
1. MTF結合で上位足の確定時刻を考慮していない可能性が発覚した。
2. M5/M15に対して、未確定だったH1/H4足をバックテスト上で使っていた可能性がある。
3. BTC M5スキャルは confirmed-time 再検証で大幅悪化した。
4. GOLDは history の最終成績と現在ライブ検出ロジックのシグナル集合がほぼ一致していなかった。
5. したがって、既存候補を延命せず、シグナル探索を最初からやり直す。
```

今後は「旧候補の再現性修復」ではなく、**confirmed-time基準でゼロから新しい候補を探索する**。

## 作業開始時に必ず読むファイル

```text
docs/NEXT_CHAT_HANDOFF.md
docs/IMPORTANT_BTC_SPREAD_REVALIDATION.md
```

BTCについてはスプレッド注意も必ず読む。ただし、この注意ファイルに過去候補が出ていても、それは履歴として扱い、採用済みとは見なさない。

## 現在やってはいけないこと

```text
- 本番ループを稼働させる
- GOLD/BTCの旧候補をDiscord通知対象に戻す
- AI評価の整備を先に進める
- 旧バックテスト成績を根拠に採用判断する
- 未確定上位足を使うMTF結合で探索する
- start time基準のmerge_asofをそのまま使う
```

次にやるべきことは、AI評価や通知ではなく、**リーク防止済みの候補探索基盤を作り直すこと**。

## 今回発覚した重要な反省点

以前、「未来情報を拾っていないか」という確認に対して、明確に否定してしまったが、それは誤りだった。

正確には、以下のような分かりやすいリークだけを見て、MTF確定時刻リークを見落としていた。

```text
- shift(-1) で未来足を直接見る
- 右側ピボット確定を使う
- 結果ラベルを特徴量へ混ぜる
```

実際に見落としていた可能性があるもの：

```text
上位足の time はバー開始時刻なのに、下位足の time とそのまま merge_asof していた。

例：
M5 00:00 に H1 00:00 を結合。
しかし H1 00:00 足が確定するのは 01:00。
ライブ時点では M5 00:00 で H1 00:00 の終値/MACD/EMAは使えない。
```

今後は、MTF結合は必ず以下を満たすこと。

```text
context_close_time <= base_close_time
```

例：

```text
M5 00:50 close_time = 00:55
H1 00:00 close_time = 01:00
=> M5 00:50ではH1 00:00を使わない

M5 00:55 close_time = 01:00
H1 00:00 close_time = 01:00
=> M5 00:55ではH1 00:00を使ってよい
```

## confirmed-time join の追加済みファイル

以下は今後の探索・検証で使う土台として残す。

```text
scripts/confirmed_time_join.py
```

主な考え方：

```text
base_close_time = base_time + base_timeframe_minutes
context_close_time = context_time + context_timeframe_minutes
merge_asof(left_on=base_close_time, right_on=context_close_time, direction='backward')
```

追加済みの確認/暫定スクリプト：

```text
scripts/run_live_gold_notifier_confirmed_from_csv.py
scripts/run_live_btc_mtf_spread_filtered_confirmed_notifier_from_csv.py
scripts/run_live_portfolio_confirmed_notifier_from_csv.py
scripts/search_btc_mtf_extra_edges_confirmed.py
scripts/revalidate_current_btc_confirmed_rules.py
scripts/revalidate_current_gold_confirmed_rules.py
scripts/audit_gold_confirmed_vs_history.py
scripts/compare_gold_history_confirmed_keys.py
scripts/fuzzy_compare_gold_history_confirmed.py
```

注意：これらは検証・監査用に作ったものであり、旧候補を採用し続けるための根拠ではない。

## BTC再検証で分かったこと

### BTC M5スキャル

旧候補：

```text
BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8
```

confirmed-time再検証結果：

```text
trades: 71
wins: 20
losses: 51
win_rate: 28.17%
total_r: -11.0R
avg_r: -0.155R
PF: 0.78
max_consecutive_losses: 12
max_dd_r: 19.0R
```

結論：

```text
採用停止。旧成績 109件 / 勝率64.22% / +101R / PF3.59 は使わない。
```

### BTC RUNNER

旧候補：

```text
BTC_RUNNER_RR2_RISK1
```

confirmed-time再検証では一応プラス：

```text
trades: 101
wins: 48
losses: 53
win_rate: 47.52%
total_r: +43.0R
avg_r: +0.426R
PF: 1.81
max_consecutive_losses: 6
max_dd_r: 6.0R
avg_effective_rr_after_spread: 1.67
```

ただし今回の方針では、これも採用済みには戻さない。白紙に戻して、次回の探索候補の比較対象または参考値としてのみ扱う。

## GOLD再検証で分かったこと

GOLDは、history上の成績と現在ライブ検出ロジックのシグナル集合がほぼ一致していなかった。

history overlap：

```text
GOLD_ABC_V3: 213件 / 勝率59.62% / +104.5R / PF2.22
GOLD_EXTRA_BB_BALANCE: 17件 / 勝率52.94% / +5.5R / PF1.69
GOLD_EXTRA_HIGH_RSI_STOCH: 19件 / 勝率68.42% / +13.5R / PF3.25
```

現在ライブ検出 confirmed-time：

```text
GOLD_ABC_V3: 66件 / 勝率13.64% / -42.52R / PF0.24
GOLD_EXTRA_BB_BALANCE: 76件 / 勝率28.95% / -24.05R / PF0.55
GOLD_EXTRA_HIGH_RSI_STOCH: 213件 / 勝率32.39% / -44.22R / PF0.69
ALL_ADOPTED: 355件 / 勝率28.17% / -110.79R / PF0.56
```

完全一致キー比較：

```text
GOLD_ABC_V3:
both 2件 / confirmed_only 64件 / history_only 211件

GOLD_EXTRA_BB_BALANCE:
both 3件 / confirmed_only 73件 / history_only 14件

GOLD_EXTRA_HIGH_RSI_STOCH:
both 14件 / confirmed_only 199件 / history_only 5件
```

結論：

```text
GOLDは旧history成績そのものより、ライブ検出実装がhistoryの最終ルールと一致していない。
ただし、旧ルール修復ではなく、新しい探索をconfirmed-time基準でやり直す。
```

## MQL5 CSV Export EA の現状

現在のEA：

```text
mql5/Experts/ExportOhlcToCsv.mq5
```

現在バージョン：

```text
#property version "1.31"
```

重要仕様：

```text
InpIncludeCurrentBar = false
InpAlignExportToMinute = true
InpExportSecond = 0
InpTimerSeconds = 1
InpAppendMode = true
InpAppendLookbackBars = 20
InpGoldM5Enabled = true
InpGoldH4Enabled = true
InpBtcM5Enabled = true
InpBtcH4Enabled = true
```

CSV出力対象：

```text
goldsharp_m5.csv
goldsharp_m15.csv
goldsharp_h1.csv
goldsharp_h4.csv
btcusdsharp_m5.csv
btcusdsharp_m15.csv
btcusdsharp_h1.csv
btcusdsharp_h4.csv
```

確認済み：

```text
GOLD M5/H4 CSV生成確認済み。
BTC M5/M15 追記モード確認済み。
```

## MT5 CSVの場所

```text
C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files
```

主なCSV：

```text
goldsharp_m5.csv
goldsharp_m15.csv
goldsharp_h1.csv
goldsharp_h4.csv
btcusdsharp_m5.csv
btcusdsharp_m15.csv
btcusdsharp_h1.csv
btcusdsharp_h4.csv
```

## bar-offset の仕様

MQL5 EA は未確定足をCSVへ出さない。
そのため、ライブで使うなら Python 側は最新CSV行を使う。

```text
--bar-offset 0
```

ただし、現時点では本番通知を止めるため、この仕様は将来再開時の注意として残す。

## runtime health log

統合wrapperには、年フォルダ/月CSVで簡潔なヘルスログを残す機能を追加済み。

保存先：

```text
data/results/live_payloads/runtime_logs/2026/portfolio_loop_health_202605.csv
```

毎分1行だけで、以下を記録する。

```text
run_started_at
run_finished_at
duration_sec
overall_returncode
gold_returncode
btc_returncode
gold_unnotified_selected
btc_raw_unnotified
btc_rejected_spread_value
btc_unnotified_selected
ledger_rows_appended
error_summary
```

ただし、現時点では本番ループは動かさない。

## BTCスプレッド注意

BTCは今後の新規探索でも、必ずスプレッド込みで検証する。

CSVの `spread` 列を使い、少なくとも以下を出すこと。

```text
mode_spread_points
mode_spread_price
net_tp_after_spread_pips
spread_to_sl_ratio
effective_rr_after_spread
net PF / net total R / max DD
```

旧BTC M5ルールのように、理論RRだけで良く見える候補を採用しない。

## 次チャットで最初にやること

方針：**候補探索を白紙から再開する。**

優先順：

```text
1. confirmed-time join を使った共通バックテスト基盤を作る
2. GOLDとBTCを分けて、シンプルな候補から再探索する
3. MTFを使う場合は context_close_time <= base_close_time を厳守する
4. BTCはスプレッド込みnet成績を必須にする
5. GOLDもM5 first-touchで勝敗判定する
6. 候補が出てもすぐ通知/AI評価へ進まず、キー・時刻・勝敗・月別成績をCSVで確認する
```

候補探索の初期方針案：

```text
GOLD:
- M15ベースを基本にする
- H1/H4を使うなら confirmed-time join
- outcomeはM5 first-touch
- まずは少数条件で件数/勝率/PF/月別/最大DDを見る

BTC:
- M15 RUNNER系から再探索
- M5スキャルは一旦後回し
- スプレッド込みnet RRを必須評価
- H1/H4はconfirmed-time join
```

## 次チャットで絶対に避けること

```text
- 旧候補を採用済みとして扱う
- GOLD/BTC通知ループを再開する
- AI評価整備を先に進める
- old history成績をそのまま根拠にする
- 未確定上位足を使うバックテストをする
- start time基準のMTF merge_asofを使う
- BTCでスプレッドなしの理論RRだけを見る
- 「未来情報はない」と検証なしに断言する
```
