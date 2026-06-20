# GOLD V3 Stage265 H1/H4 intrabar breakout監査

作成日: 2026-06-21  
正式状態: `GOLD_V3_265_H4_INTRABAR_BREAKOUT_PROMISING_NOT_VALIDATED_AUDIT_ONLY`

## 結論

確定済みH1/H4からpending stop水準を事前固定し、その後のM1到達で約定する方式を監査した。

- H1 intrabar: REJECTED
- H4 intrabar: PROMISING NOT VALIDATED

H4は67件、cost2期待値+3.692 USD、PF1.418、PnL+247.39 USD。2025 M1 source区間と2026 M1 source区間、LONGとSHORTの全てがcost2でプラスだった。

ただし2025/2026は既知期間で、M1 source連続性、official calendar、spread path、slippage、swap、新規future holdoutが不足するためlive-readyではない。

## 時刻・因果契約

- CSV行は確定足、timeはOPEN時刻。
- H1情報はtime+1時間、H4はtime+4時間、D1はtime+1日から利用。
- 水準・方向・ATR・SL・TP・期限はdecision_timeで固定。
- M1は事前注文のgap/touchとexit順序だけに使用。
- M1 high/lowを見て同じM1 openへ遡る処理はない。
- 同一M1のentry+SLまたはTP+SLはSL優先。

## H1結果

- resolved: 104
- cost2 PnL: -217.34
- expectancy: -2.090
- PF: 0.738
- cost5 expectancy: -5.090
- max DD: 293.53

2025区間は赤字。LONGもcost2赤字。事前基準を満たさずREJECT。

## H4結果

- resolved: 67
- cost2 PnL: +247.39
- expectancy: +3.692
- PF: 1.418
- win rate: 55.22%
- max DD: 157.77
- gap fill rate: 1.49%
- cost5 PnL: +46.39
- cost5 expectancy: +0.692
- cost5 PF: 1.067

### source別 cost2

- 2025 GOLD_HASH: 52件、PnL +198.30、期待値 +3.813、PF1.606
- 2026 GOLDSHARP: 15件、PnL +49.10、期待値 +3.273、PF1.186

### 方向別 cost2

- LONG: 57件、PnL +124.68、期待値 +2.187、PF1.289
- SHORT: 10件、PnL +122.71、期待値 +12.271、PF1.767

### exit

- TIME_EXIT: 54件、PnL +306.31
- TP_EXIT: 4件、PnL +250.92
- SL_EXIT: 9件、PnL -309.84

利益の中心は、早いintrabar entry後に8時間保有したTIME_EXITと少数TPだった。

## Stage264との比較

2025〜2026のH4:

- close確認後の次H4 OPEN: 71件、期待値+0.129、PF1.015、PnL+9.13
- 事前stopのintrabar entry: 67件、期待値+3.692、PF1.418、PnL+247.39

この比較は、H4をentry timeframeにすることではなく、H4 closeブレイク確定まで待つ執行遅延が問題だったという指摘を支持する。

## correctness

- candidate prefix parity: 12/12 PASS
- prefix streaming replay: 16/16 PASS
- regression tests: 4/4 PASS
- replay最大数値差: 4.55e-13以下

途中の実装で未来のM1欠損を先に確認する不備を検出し、欠損が実際に到来した時点だけで状態変更するstreaming方式へ修正した。修正前後の成績数値は同じだった。

## 事前合否

H4は11項目を全てPASS。H1はexpectancy、PF、cost5、方向・source安定性でFAIL。

## 注意

H4のcost5余裕は小さい。全体期待値は+0.692 USD、PF1.067で、LONG単独はcost5赤字。spread/slippageが少し悪化するとedgeが消える可能性がある。

2026 source区間は15件だけであり、統計的確証には不足する。これはEA採用ではなく、次段階へ残す候補判定。

## 次段階

Stage266ではparameterを変更せず、H4 intrabar候補について次だけを行う。

1. broker spread/slippage stress
2. official session calendar binding
3. swap/rollover不要の同日内contract確認
4. MT5 batch/streaming state machine実装
5. 新しいfuture paper holdout

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
