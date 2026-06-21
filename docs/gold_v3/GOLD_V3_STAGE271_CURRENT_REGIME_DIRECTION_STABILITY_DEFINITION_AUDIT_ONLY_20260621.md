# GOLD V3 Stage271 定義固定
## Current-regime direction-stability diagnostic

作成日: 2026-06-21
状態: `GOLD_V3_271_CURRENT_REGIME_DIRECTION_STABILITY_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

Stage270で現在最も維持されたR2と、直近でSHORT偏重となったR3について、方向別の崩れをentry時点既知特徴から診断する。

新しいentry trigger、閾値、gate、SL/TP、portfolioは作らない。R1はresearch-onlyのまま対象外。

## 対象regime

### R2
- H1 UTC08-11 × HIGH volatility
- direction=BAR_CONTINUATION
- fixed horizon=48 trading hours

### R3
- H1 INDECISION × RANGE
- direction=BAR_CONTINUATION
- fixed horizon=8 trading hours

## 期間

- 2025 full source period
- 2026 pre-recent60
- 2026 latest90
- 2026 latest60
- 2026 latest30

latest基準はStage270 data end `2026-06-19 19:00:00`で固定。

## 絶対契約

- audit-only。
- GOLD V2、旧GOLD、DISC8、Stage41を読まない。
- Stage268 H1 enriched pathを使用。
- entry featureはdecision時点既知の列だけ。
- future return、MFE、MAE、path timingは診断label/結果にのみ使用。
- source identity・direction・年・月をprediction featureに使わない。
- LONG only / SHORT only化禁止。
- 結果後の閾値調整禁止。
- live promotion禁止。

## 固定entry-known numeric features

- h1_atr14
- h1_atr_ratio
- h1_atr_pct100
- h1_range_atr
- h1_body_range
- h1_rsi14
- h1_macd_hist_atr
- h1_ema_spread_signed_atr
- h1_ema_slope3_atr
- h1_range_pos20
- h1_extension_aligned
- d1_direction
- d1_ema_spread_abs_atr
- d1_ema_slope3_atr
- d1_atr_ratio
- d1_rsi14
- d1_macd_hist_atr
- h4_direction
- h4_ema_spread_abs_atr
- h4_ema_slope3_atr
- h4_atr_ratio
- h4_rsi14
- h4_macd_hist_atr
- activation_delay_minutes

方向に対する整列featureを追加する:

- d1_direction * regime_direction
- h4_direction * regime_direction
- h1 RSI centered * regime_direction
- H1/H4/D1 slope・MACD・EMA spreadをregime方向へ整列

## 固定categorical features

- d1_alignment
- h1_h4_d1_alignment
- h1_expansion_state
- h1_extension_bucket
- h1_candle_state
- activation_state
- decision_weekday

## 診断

### 1. Outcome decomposition

方向×期間ごとに:

- n
- positive rate
- mean/median return
- mean/median MFE/MAE
- early 4h/8h/24h return
- persistent/delayed/fade/no-direction比率

### 2. Univariate winner-loss diagnostics

各方向・期間でwinner vs loserを比較:

- standardized mean difference
- median shift / pooled IQR
- point-biserial correlation
- quartile/bin positive rate
- category positive rate

### 3. Recent direction divergence diagnostics

- R2 latest60 LONG vs SHORT
- R3 latest60 LONG vs SHORT
- recent losers vs historical same-direction winners
- recent winners vs recent losers

### 4. Pairwise interactions

固定category/numeric bucketの2軸組合せを診断する。

- D1 aligned direction × H4 aligned direction
- D1 aligned direction × H1 extension bucket
- H4 aligned direction × H1 extension bucket
- H1 ATR ratio bucket × D1 aligned direction
- H1 range position bucket × H4 aligned direction
- H1 body/range bucket × D1 aligned direction

minimum n:
- overall cell >=20
- direction-period cell >=8

### 5. Descriptive model benchmark

目的はgate作成ではなく、entry-known特徴でdirection divergenceが説明可能か確認すること。

- LogisticRegression elastic-net
- RandomForest max_depth=3, min_samples_leaf=12
- GradientBoosting max_depth=2, min_samples_leaf=12

training:
- 2025 + 2026 pre-latest60

test:
- 2026 latest60

featureにsource/year/month/directionは入れない。

出力:
- AUC
- Brier score
- positive-rate calibration terciles
- permutation importance
- model間重要feature一致

### 6. Matched diagnostics

最近の各lossを、同regime・同directionの過去candidateから以下を優先してnearest matchする:

- H1 ATR percentile
- H1 ATR ratio
- H1 extension
- D1/H4 aligned direction
- D1 slope
- H4 slope

最近lossとhistorical matched controlのfeature差・return差を出す。

## cause分類

### STABLE_ENTRY_KNOWN_CAUSE

- 同じfeatureまたはinteractionが2025、2026 pre-recent、latest60で同じ方向にwinner/lossを分離
- minimum direction-period n>=15
- |SMD|>=0.35またはcategory positive-rate差>=10pp
- descriptive model importance上位5へ2model以上で出現

### RECENT_REGIME_ASSOCIATION_ONLY

- latest60で差があるが2025またはpre-recentで同符号にならない

### PATH_TIMING_SHIFT_NOT_ENTRY_SEPARABLE

- recent failureがMFE/MAE・fade/delayedで変化するがentry-known model AUC<0.60

### INSUFFICIENT_SAMPLE

- direction-period n<15

## Stage271合格条件

- R2/R3 direction-period outcome decomposition生成
- numeric/category/pairwise diagnostics生成
- model benchmark生成
- matched diagnostics生成
- future feature leakage 0
- model featureからsource/year/month/direction除外
- regression tests全PASS

## 次段階

Stage272では:

- `STABLE_ENTRY_KNOWN_CAUSE`がある場合のみ、固定featureをcandidate-quality filterとしてpre-registered OOF評価
- `RECENT_REGIME_ASSOCIATION_ONLY`なら新gateを作らず監視
- `PATH_TIMING_SHIFT_NOT_ENTRY_SEPARABLE`ならentryではなくexit/horizon研究へ進む

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
