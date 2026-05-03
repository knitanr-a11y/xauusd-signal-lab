# IMPORTANT: BTCUSD# spread revalidation warning

このドキュメントは、新しいチャットへ移行したときに最初に必ず読むこと。

## 結論

BTCUSD# の検証・通知・AI評価では、必ず実運用スプレッドを考慮する。

これまで追加検討していた `BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8` は、スプレッド考慮が不十分な状態で候補化していたため、現時点では **未採用・再検証対象** とする。

`BTC_RUNNER_RR2_RISK1` も含め、BTC系ルールはスプレッド込みで再集計するまで最終採用扱いにしない。

## スプレッド採用ルール

BTCの検証では、固定20ドルを無条件採用してはいけない。

MT5/MQL5 CSVに `spread` 列がある場合は、まずCSV内で一番頻出している `spread` 値を採用する。

```text
採用スプレッド価格 = mode(spread列) × point_size
```

現在の再検証スクリプトでは、デフォルトで以下の方針にする。

```text
--spread-mode csv_mode
--spread-source m5
--point-size 0.01
--pip-size 10
```

固定値を使うのは、CSVのspread列が壊れている、または比較検証したい場合だけ。

```text
--spread-mode fixed --assumed-spread-price 20
```

## 背景

BTCUSD# は実運用スプレッドが大きい。
ユーザーの運用前提では、BTCの想定スプレッドはおおむね以下の認識。

```text
BTCUSD# spread = 約20ドル
BTCUSD# pip size = 約10ドル
20ドル = 約2 pips
```

ただし、実際にはCSVの `spread` 列に履歴値があるため、再検証ではCSVの最頻値を優先する。

そのため、ATRベースで出した理論上のTP/SLだけを見ると成績を過大評価する。

例：

```text
Entry 78428.90
TP    78481.28
SL    78402.71

理論TP幅: +52.38ドル = 約5.24 pips
理論SL幅: -26.19ドル = 約2.62 pips
想定スプレッド: 20.00ドル = 約2.00 pips
```

スプレッドを考慮すると、実質は以下のようになる。

```text
実質TP幅 = 52.38 - 20.00 = 32.38ドル = 約3.24 pips
実質SL負担 = 26.19 + 20.00 = 46.19ドル = 約4.62 pips
理論RR = 2.0
実質RR = 32.38 / 46.19 = 約0.70
spread / SL = 20.00 / 26.19 = 約76.4%
spread / TP = 20.00 / 52.38 = 約38.2%
```

この状態では、理論上RR2.0でも実質RRが大きく悪化する。
そのため、バックテスト上のPFもスプレッド込みで再計算すると大きく低下する可能性が高い。

## 重要な反省点

以前の実装では、通知側で以下を後から追加しただけだった。

- 理論TP/SL価格
- 想定スプレッド表示
- 実質TP幅
- 実質SL負担
- spread/SL比率
- 実質RR

しかし、本来は通知より先に、検証・探索・採用判断の段階でBTCスプレッドを考慮すべきだった。

特に `BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8` は、M5高頻度ルールであり、値幅が小さいためスプレッド影響が非常に大きい。
このルールはスプレッド込み再検証前に採用扱いしてはいけない。

## 新チャットで必ず守ること

新しいチャットに移行したら、まずこのファイルを読むこと。

対象ファイル：

```text
docs/IMPORTANT_BTC_SPREAD_REVALIDATION.md
```

そして、以下を前提に作業を再開すること。

```text
1. BTC系ルールはスプレッド込みで再検証する
2. BTCスプレッドはCSV spread列の最頻値を優先する
3. BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8 は未採用に戻す
4. BTC RUNNER もスプレッド込み成績を確認する
5. 通知・AI評価だけでなく、探索スクリプトとバックテスト自体にスプレッドコストを反映する
6. PF、total R、勝率、最大DD、実質RRを再計算する
7. スプレッド控除後も成立するBTCルールだけを採用候補にする
```

## 再検証で必要な指標

BTCルール再検証では、最低限以下を出す。

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

## BTC通知で必ず表示する項目

BTC通知では、理論値だけでなく必ず以下を表示する。

```text
価格目安:
Entry / TP / SL

理論値幅:
TP幅ドル / TP pips
SL幅ドル / SL pips

スプレッド考慮:
採用スプレッドドル / spread pips
実質TP幅ドル / 実質TP pips
実質SL負担ドル / 実質SL pips

コスト比率:
spread/SL
spread/TP
実質RR

注意:
spread/SL が大きい場合は慎重または見送り候補
```

## AI評価で必ず渡す項目

AI評価payloadにも、BTCでは必ず以下を含める。

```text
btc_assumed_spread_price
btc_pip_size
gross_tp_pips
gross_sl_pips
net_tp_after_spread_price
net_tp_after_spread_pips
sl_with_spread_price
sl_with_spread_pips
spread_to_sl_ratio
spread_to_tp_ratio
effective_rr_after_spread
spread_warnings
```

AI評価は、BTCでは理論RRではなく、スプレッド控除後の実質RRとspread/SL比率を重視する。

## 次にやること

次の作業はAI評価拡張ではなく、BTCルールの再検証からやり直す。

優先順：

```text
1. CSV spread列の最頻値を確認
2. BTC_SCALP_H1_M5_REENTRY_FILTERED をCSV最頻スプレッド込みで再バックテスト
3. BTC_RUNNER_RR2_RISK1 をCSV最頻スプレッド込みで再バックテスト
4. net PF / net total R / effective RR を確認
5. PFが大きく落ちる場合、BTC M5ルールは除外またはSL/TP幅を広げる方向で再探索
6. 採用ポートフォリオもBTCスプレッド込みで再集計
```

## 絶対に避けること

```text
- BTCでATRベースの理論TP/SLだけを見て採用判断する
- スプレッド込みPFを確認せずにBTC M5ルールを採用扱いする
- CSVにspread列があるのに固定20ドルだけで検証する
- 通知側だけスプレッド表示して、バックテスト側で反映しない
- AI評価に理論RRだけ渡して実質RRを渡さない
```
