# IMPORTANT: BTCUSD# spread-aware and confirmed-time policy

このドキュメントは、新しいチャットへ移行したときに最初に必ず読むこと。

## 最重要結論：BTC候補は一旦白紙

2026-05-06時点で、BTCの既存候補は採用済みとして扱わない。

```text
BTC_RUNNER_RR2_RISK1
BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8
```

上記は、次回以降の探索で比較対象・参考値として見ることはあっても、採用候補・通知対象・AI評価対象として扱わない。

特にBTC M5スキャルは confirmed-time 再検証で明確に崩れたため、採用停止。

## なぜ白紙に戻すのか

BTCでは2つの重要問題が発覚した。

```text
1. スプレッド考慮不足
2. MTF上位足の確定時刻を考慮しない結合
```

スプレッドだけでなく、MTF結合も重要。

上位足の `time` はバー開始時刻であり、そのバーがその時刻に確定しているわけではない。

悪い例：

```text
M5 00:00 に H1 00:00 を結合する
```

H1 00:00足が確定するのは01:00なので、これはライブ時点では使えない情報。

今後の正しい条件：

```text
context_close_time <= base_close_time
```

例：

```text
M5 00:50 close_time = 00:55
H1 00:00 close_time = 01:00
=> 使わない

M5 00:55 close_time = 01:00
H1 00:00 close_time = 01:00
=> 使ってよい
```

## confirmed-time BTC再検証結果

### BTC M5スキャル

旧候補：

```text
BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8
```

confirmed-time + spread-aware 再検証：

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
avg_net_tp_pips: 20.31
avg_spread_to_sl_ratio: 0.247
avg_effective_rr_after_spread: 1.42
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

confirmed-time + spread-aware 再検証：

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
avg_net_tp_pips: 48.20
avg_spread_to_sl_ratio: 0.127
avg_effective_rr_after_spread: 1.67
```

結論：

```text
一応プラスだが、今回の方針では採用済みに戻さない。
白紙からの再探索で比較対象としてのみ扱う。
```

## BTCスプレッド方針は継続

BTC系ルールは、ATRベースの理論TP/SLだけで採用判断してはいけない。

必ずCSVの `spread` 列を考慮する。

```text
採用スプレッド価格 = mode(spread列) × point_size
```

現在のBTCUSD# CSVでは、直近確認時点で以下が出ていた。

```text
mode_spread_points: 2250
mode_spread_price: 22.5
pip_size: 10
```

つまり、BTCUSD#のスプレッドは約22.5ドル、約2.25pipsとして扱われていた。

ただし、今後の探索では毎回CSVから再計算すること。

## 今後のBTC探索で必須の評価指標

BTCでは、以下を最低限出す。

```text
- spread_mode
- spread_source
- mode_spread_points
- mode_spread_price
- gross_total_r
- net_total_r_after_spread
- gross_pf
- net_pf_after_spread
- gross_avg_r
- net_avg_r_after_spread
- gross_win_rate
- net_win_rate_after_spread
- max_consecutive_losses
- max_dd_r_after_spread
- trades_per_month
- avg_gross_tp_distance_price
- avg_gross_sl_distance_price
- avg_spread_price
- avg_spread_to_sl_ratio
- avg_spread_to_tp_ratio
- avg_effective_rr_after_spread
```

採用判断では、理論RRではなく、スプレッド控除後の実質RR・PF・DDを見る。

## 今後のBTC探索で必須のMTF条件

MTFを使う場合は、必ず confirmed-time join を使う。

```text
scripts/confirmed_time_join.py
```

基本式：

```text
base_close_time = base_time + base_timeframe_minutes
context_close_time = context_time + context_timeframe_minutes
context_close_time <= base_close_time
```

start time基準の以下のような結合は、探索・バックテストでは使わない。

```python
pd.merge_asof(
    base.sort_values('time'),
    context.sort_values('context_time'),
    left_on='time',
    right_on='context_time',
    direction='backward',
)
```

## 本番通知について

現時点では、BTC本番通知は再開しない。

以下のスクリプトは存在するが、次チャットでは採用済みとして使わない。

```text
scripts/run_live_btc_mtf_spread_filtered_notifier_from_csv.py
scripts/run_live_btc_mtf_spread_filtered_confirmed_notifier_from_csv.py
scripts/run_live_portfolio_confirmed_notifier_from_csv.py
scripts/run_live_portfolio_notifier_loop.bat
```

通知より先に、白紙から confirmed-time + spread-aware の探索をやり直す。

## 旧履歴として残すが採用根拠にしない情報

過去に以下のような結果が出ていた。

```text
BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8:
109件 / 勝率64.22% / +101.0R / PF3.59

BTC_RUNNER_RR2_RISK1:
77件 / 勝率61.04% / +64.0R / PF3.13
```

しかし、これらはMTF確定時刻リークの可能性があるため、今後の採用根拠にはしない。

## 次チャットでやること

```text
1. docs/NEXT_CHAT_HANDOFF.md を読む
2. docs/IMPORTANT_BTC_SPREAD_REVALIDATION.md を読む
3. BTC候補を白紙から再探索する
4. confirmed-time join を必ず使う
5. spread-aware net成績を必ず出す
6. M5スキャルは後回し。まずM15以上の比較的安定した候補から探す
```

## 絶対に避けること

```text
- BTC旧候補を採用済みとして扱う
- BTC M5スキャルを通知対象に戻す
- スプレッドなしの理論RRだけを見る
- start time基準のMTF merge_asofを使う
- confirmed-time再検証なしでAI評価へ進む
- 本番通知を先に再開する
```
