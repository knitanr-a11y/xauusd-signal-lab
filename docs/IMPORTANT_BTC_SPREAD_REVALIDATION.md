# IMPORTANT: BTCUSD# spread-aware adoption policy

このドキュメントは、新しいチャットへ移行したときに最初に必ず読むこと。

## 結論

BTCUSD# の検証・通知・AI評価では、必ず実運用スプレッドを考慮する。

BTC系ルールは、ATRベースの理論TP/SLだけで採用判断してはいけない。必ず以下を使う。

```text
採用スプレッド価格 = mode(spread列) × point_size
```

現時点のBTC採用候補は以下。

```text
1. BTC_RUNNER_RR2_RISK1
   - 採用候補維持
   - スプレッド込みでも成立

2. BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8
   - 無条件採用は禁止
   - CSV最頻スプレッド + 値幅フィルタ通過時のみ通知・採用候補
```

## 最新の再検証結果

再検証で使用したスプレッドは、M5 CSVの `spread` 列の最頻値。

```text
mode_spread_points: 2250
mode_spread_price: 22.5
sample_count: 30000
pip_size: 10
```

つまり、今回のBTCUSD# CSVでは以下として扱う。

```text
採用スプレッド: 22.5ドル
pip換算: 約2.25 pips
```

### BTC M5 REENTRY FILTERED

対象：

```text
BTC_SCALP_H1_M5_REENTRY_FILTERED
RR 2.0
risk_atr 0.8
max_bars 72/144/288
```

スプレッド・値幅フィルタ後：

```text
before: 120件
after: 109件
除外: 11件

勝率: 64.22%
total: +101.0R
平均: +0.927R
PF: 3.59
最大DD: 4.0R
最大連敗: 4
月平均: 21.8件
```

値幅面：

```text
平均 実質TP幅: 約20.76 pips
平均 実質SL負担: 約13.76 pips
平均 spread/SL: 23.33%
平均 実質RR: 1.45
adoption_candidate: True
```

結論：

```text
BTC M5追加ルールは、低値幅シグナルを除外する前提なら採用候補に戻す。
ただし、値幅フィルタを通過しないシグナルは通知しない。
```

### BTC RUNNER

対象：

```text
BTC_RUNNER_RR2_RISK1_REVALIDATED
RR 2.0
risk_atr 1.0
```

スプレッド込み結果：

```text
77件
勝率: 61.04%
total: +64.0R
PF: 3.13
最大DD: 4.0R
最大連敗: 4
月平均: 6.42件
平均 実質TP幅: 45.18 pips
平均 実質SL負担: 25.97 pips
平均 spread/SL: 12.54%
平均 実質RR: 1.68
adoption_candidate: True
```

結論：

```text
BTC RUNNERはスプレッド込みでも採用候補維持。
```

## BTC M5の必須値幅フィルタ

BTC M5追加ルールは、以下を通過した場合だけ通知・採用候補にする。

```text
net_tp_after_spread_pips >= 5.0
spread_to_sl_ratio < 0.50
effective_rr_after_spread >= 1.0
```

直近の小幅シグナル例：

```text
2026-05-03 14:05 BUY
net_tp_after_spread_pips = 2.99
spread_to_sl_ratio = 85.9%
effective_rr_after_spread = 0.61
```

このようなシグナルは、検出されても通知しない。

```text
シグナル検出: True
通知: False
理由:
- 実質TP幅が小さすぎる
- spread/SLが大きすぎる
- 実質RRが悪い
```

## 本番BTC通知スクリプト

BTCの本番通知は、以下を使う。

```text
scripts/run_live_btc_mtf_spread_filtered_notifier_from_csv.py
```

旧スクリプトは参考・開発用扱い。

```text
scripts/run_live_btc_mtf_notifier_from_csv.py
```

旧スクリプトをBTC本番通知に使わないこと。

本番BTC通知は以下を必ず行う。

```text
1. CSV spread列の最頻値を取得
2. spread価格 = mode(spread) × point_size
3. 実質TP幅を計算
4. spread/SL比率を計算
5. スプレッド控除後の実質RRを計算
6. 値幅条件を満たさないBTCシグナルは通知しない
7. AI評価にもスプレッド込みtrade_planを渡す
```

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
BTCUSD# spread = 約20ドル前後
BTCUSD# pip size = 約10ドル
20ドル = 約2 pips
```

ただし、実際にはCSVの `spread` 列に履歴値があるため、再検証ではCSVの最頻値を優先する。

ATRベースで出した理論上のTP/SLだけを見ると成績を過大評価する。

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

このような低値幅シグナルは、理論上RR2.0でも実質RRが大きく悪化するため、通知しない。

## 重要な反省点

以前の実装では、通知側で以下を後から追加しただけだった。

- 理論TP/SL価格
- 想定スプレッド表示
- 実質TP幅
- 実質SL負担
- spread/SL比率
- 実質RR

しかし、本来は通知より先に、検証・探索・採用判断の段階でBTCスプレッドを考慮すべきだった。

特に `BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8` は、M5高頻度ルールであり、値幅が小さいシグナルが混ざるためスプレッド影響が非常に大きい。

## 新チャットで必ず守ること

新しいチャットに移行したら、まずこのファイルを読むこと。

対象ファイル：

```text
docs/IMPORTANT_BTC_SPREAD_REVALIDATION.md
```

そして、以下を前提に作業を再開すること。

```text
1. BTC系ルールは必ずスプレッド込みで扱う
2. BTCスプレッドはCSV spread列の最頻値を優先する
3. BTC M5追加ルールは値幅フィルタ通過時のみ通知・採用候補
4. BTC RUNNERはスプレッド込み成績を確認済みの採用候補
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

次の作業候補：

```text
1. BTCの本番通知コマンドを spread_filtered 版に統一する
2. GOLD通知側へ進む
3. GOLD/BTC統合ライブ通知スクリプトを作る
4. 最後にGOLD/BTC統合ポートフォリオを、BTC値幅フィルタ込みで再集計する
```

## 絶対に避けること

```text
- BTCでATRベースの理論TP/SLだけを見て採用判断する
- スプレッド込みPFを確認せずにBTC M5ルールを採用扱いする
- CSVにspread列があるのに固定20ドルだけで検証する
- 通知側だけスプレッド表示して、バックテスト側で反映しない
- AI評価に理論RRだけ渡して実質RRを渡さない
- BTC本番通知に旧スクリプトを使う
```
