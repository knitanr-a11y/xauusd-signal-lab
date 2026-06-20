# GOLD V3 Stage263 定義固定
## 研究設計リセット＋2026年6月擬似holdout

作成日: 2026-06-20  
状態: `GOLD_V3_263_RESEARCH_ARCHITECTURE_RESET_JUNE_PSEUDO_HOLDOUT_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

手作業のsetup探索を停止し、各M15確定時点で60分後の価格変化を予測し、LONG・SHORT・NO TRADEを選ぶ単純な意思決定モデルへ切り替える。

2026年6月1日〜19日は過去のStageで一部集計を見ているため完全未見ではない。したがって最終holdoutではなく、設計が明確に失敗していないかを一度だけ確認する`contaminated pseudo-holdout`として扱う。

6月結果を見た後に特徴量、モデル、threshold、方向、保有時間、取引時間帯を変更しない。

## 絶対契約

- audit-only。
- GOLD V2、旧GOLD、DISC8、Stage41を読まない。
- E2〜E8を直接entryルールとして使用しない。
- Stage263初回baselineではE2〜E8フラグも特徴量へ入れない。手作業setupの影響を外した状態で新設計そのものを評価する。
- 2026年6月を学習、feature selection、threshold選択、モデル選択に使わない。
- 6月結果確認後のLONGのみ、SHORTのみ、時間帯除外、threshold変更は禁止。
- MT5発注、通知、live hook、order payload、autotrade、final signal禁止。

## データ期間

### 開発期間

- 2025-01-02 から 2026-05-31まで。
- walk-forward予測期間は2025-07-01から2026-05-31。
- 各月は、その月より前のデータだけでfitするexpanding window。
- 最低6か月分の学習履歴を必要とする。

### 擬似holdout

- 2026-06-01 00:00:00以上、2026-06-20 00:00:00未満。
- final modelは2026-05-31以前だけでfit。
- 6月を一度だけ推論する。

## decision / entry / exit

- decision bar: 完了M15。
- CSV timeはM15 OPEN時刻。
- decision_time = M15 time + 15分。
- entry_time = decision_time。
- entry_price = entry_timeに始まるexact M1 OPEN。
- exit_time = entry_time + 60分。
- exit_price = exit_timeに始まるexact M1 OPEN。
- exact M1がentryまたはexitにない場合はそのdecisionを`DATA_MISSING_NO_LABEL_OR_TRADE`とし、近傍時刻へfallbackしない。
- 保有中は新規tradeを作らない。`entry_time < active_until`を抑制し、active_until = exit_time。

## entry-known safe window

pre-known broker holiday calendarがない状態でsession端を跨がないため、次だけを対象とする。

- 月曜〜金曜。
- decision_timeのUTC時刻が08:00以上18:00未満。

これは6月結果を見ずに固定した保守的なoperational windowであり、後から変更しない。

## 予測target

M15確定時点の因果ATR14を使用する。

- `gross_return_usd = exit_open - entry_open`
- `target_norm = gross_return_usd / atr14_m15`

LONGとSHORTを別labelにせず、符号付き60分returnを予測する。

評価時:

- LONG gross PnL = exit_open - entry_open
- SHORT gross PnL = entry_open - exit_open
- cost2 PnL = gross PnL - 2.0 USD

固定TP/SLは使用しない。

## 因果特徴量

現在M15を含む完了足までだけを使用する。

### M15価格・形状

- return 1 / 2 / 4 / 8 / 16 bars
- closeのEMA8 / EMA20 / EMA50からのATR正規化距離
- EMA8-EMA20、EMA20-EMA50のATR正規化差
- EMA8 / EMA20 / EMA50の1・4bar slope
- ATR14、ATR50、ATR14/ATR50
- rolling return標準偏差 8 / 32 bars
- body/range、upper wick/range、lower wick/range
- current true range / ATR14
- close location in bar range
- RSI14
- tick_volume / rolling median 32
- tick_volume causal z-score 64
- spread / rolling median 64

### 時刻

- UTC hour sin / cos
- weekday sin / cos

### H1 / H4

source_close_time <= decision_timeを満たす最後の完了H1/H4だけをas-of結合する。

- H1 return 1 / 3 / 6 bars
- H1 EMA8-EMA20 / H1 ATR14
- H1 close-EMA20 / H1 ATR14
- H1 ATR14/ATR50
- H4 return 1 / 3 bars
- H4 EMA5-EMA12 / H4 ATR14
- H4 close-EMA12 / H4 ATR14
- H4 ATR14/ATR50

絶対価格そのものは特徴量へ入れない。

## 欠損処理

- rolling warm-up不足は行を除外。
- model入力の残存NaNはtraining medianでimputeする。
- 6月medianを計算しない。

## 固定model

### Model A: Ridge

- `SimpleImputer(strategy="median")`
- `StandardScaler()`
- `Ridge(alpha=10.0)`

### Model B: HistGradientBoostingRegressor

- `loss="squared_error"`
- `learning_rate=0.05`
- `max_iter=200`
- `max_leaf_nodes=15`
- `max_depth=3`
- `min_samples_leaf=100`
- `l2_regularization=1.0`
- `random_state=263`

両modelは同じtarget_normを予測する。

## ensembleとNO TRADE

各時点で:

- `ridge_usd = ridge_pred_norm * atr14_m15`
- `hgb_usd = hgb_pred_norm * atr14_m15`
- `ensemble_usd = (ridge_usd + hgb_usd) / 2`

signal条件:

1. ridge_usdとhgb_usdの符号が一致。
2. `abs(ensemble_usd) >= frozen_edge_threshold_usd`。
3. exact entry/exit M1が存在。
4. safe window内。
5. portfolioにactive tradeがない。

方向:

- ensemble_usd > 0: LONG
- ensemble_usd < 0: SHORT
- その他: NO TRADE

## threshold固定

2025-07〜2026-05のwalk-forward OOF予測だけを使う。

- 両model符号一致時の`abs(ensemble_usd)`の85 percentileを計算。
- `frozen_edge_threshold_usd = max(3.0, OOF 85 percentile)`。

6月分布をthresholdへ使用しない。

## baselines

同じsafe window、同じentry/exit、同じone-active 60分、cost2で比較する。

- `ALWAYS_LONG`
- `ALWAYS_SHORT`
- `PREV_BAR_DIRECTION`: 完了M15のclose-open符号
- `EMA_TREND`: EMA20>EMA50ならLONG、EMA20<EMA50ならSHORT

baseline thresholdはない。

## 開発walk-forward監査

OOFで次を表示する。

- prediction MAE / RMSE
- predictionとrealized gross_returnのPearson / Spearman
- signal trade count
- cost2 expectancy / PF / PnL / max drawdown
- 月別PnL
- direction別
- confidence tercile別
- baseline比較

OOFが赤字でも定義は変更せず、6月はarchitecture rejection確認のため一度だけ実行する。

## 6月擬似holdout合否

`JUNE_PSEUDO_HOLDOUT_PROMISING_NOT_VALIDATED`には全て必要。

1. model trade数15件以上。
2. cost2 expectancy > 0。
3. PF >= 1.10。
4. model cost2 PnLが4 baselinesの最大PnLを上回る。
5. model max drawdownがmodel gross profitの100%以下。
6. confidence上位半分のexpectancyが下位半分以上。
7. 単一tradeが総positive PnLの50%以上を占めない。
8. batch feature/predictionとprefix再計算が完全一致。

いずれか失敗:

`JUNE_PSEUDO_HOLDOUT_REJECTED`

合格してもlive-readyではなく、新しい未来paper holdoutが必要。

## formal states

- `GOLD_V3_263_JUNE_PSEUDO_HOLDOUT_PROMISING_NOT_VALIDATED_AUDIT_ONLY`
- `GOLD_V3_263_JUNE_PSEUDO_HOLDOUT_REJECTED_AUDIT_ONLY`
- `GOLD_V3_263_DATA_OR_PARITY_BLOCKED_AUDIT_ONLY`

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
