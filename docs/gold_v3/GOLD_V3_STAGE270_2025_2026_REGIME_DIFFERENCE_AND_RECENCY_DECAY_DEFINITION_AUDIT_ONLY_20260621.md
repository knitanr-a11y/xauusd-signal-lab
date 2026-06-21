# GOLD V3 Stage270 定義固定
## 2025–2026 regime difference and 2026 recency decay audit

作成日: 2026-06-21
状態: `GOLD_V3_270_2025_2026_REGIME_DIFFERENCE_AND_RECENCY_DECAY_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

Stage268/269で残ったH1 regimeが、2025年と2026年の相場構造差によってなぜ強弱を変えたかを診断する。また2026年内で性能が維持・劣化・反転しているかを月別、rolling、直近60日、直近30日で評価する。

Stage270では新しいentry trigger、閾値、SL/TP、portfolioを作らない。

## 絶対契約

- audit-only。
- GOLD V2、旧GOLD、DISC8、Stage41を読まない。
- Stage268のH1/H4 enriched pathとStage269の固定regimeだけを使用。
- 2025/2026のsource identityを維持し混合しない。
- ATR正規化済みreturn/MFE/MAEを使用し、価格水準差をedgeと誤認しない。
- C1/F12その他旧候補はREFERENCE_ONLY_NOT_VALIDATEDのまま。
- 新しい条件や閾値を結果後に追加しない。
- live promotion禁止。

## 比較対象

### 全市場構造

H1/H4で2025・2026を比較する。

- ATR14実値、ATR14/ATR50、ATR percentile100
- trend_state比率
- volatility_bucket比率
- expansion_state比率
- extension_bucket比率
- candle_state比率
- D1 alignment比率
- H1/H4/D1 alignment比率
- decision hour / hour-bin比率
- observed closure後activation比率
- D1 direction、H1/H4 direction比率
- 4/8/24/48/72/120h MFE/MAE/return分布

### 固定regime

- R1 H1 WEAK_TREND × LOW volatility / TIMEFRAME_TREND / 48h
- R2 H1 UTC08-11 × HIGH volatility / BAR_CONTINUATION / 48h
- R3 H1 INDECISION × RANGE / BAR_CONTINUATION / 8h

R2 72hは補助比較のみ。

## 分布差指標

### 数値feature

- count、mean、median、std、q10/q25/q75/q90
- standardized mean difference
- median shift normalized by 2025 IQR
- PSI（2025 quantile binsを固定）

PSI interpretation:
- <0.10: stable
- 0.10–0.25: moderate shift
- >=0.25: material shift

### category feature

- 構成比
- percentage-point change
- Jensen-Shannon divergence

## regime performance差

各R1/R2/R3について:

- 2025、2026
- 年月別
- LONG/SHORT別
- source×direction別
- positive rate
- mean/median return ATR
- median MFE/MAE
- MFE/|MAE|比
- persistent/delayed/fade/no-direction比率

## recency windows

2026年の最終利用可能decision時刻を基準に:

- 月別
- rolling 60 calendar days
- rolling 90 calendar days
- latest 60 days
- latest 30 days
- first half of available 2026
- second half of available 2026

rolling窓は各decisionのdecision_timeで切る。

## decay判定

### CURRENTLY_MAINTAINED

- latest60 n>=20
- latest60 mean>0、median>0
- LONG/SHORT各5件以上
- LONG/SHORT双方mean>=0
- latest60 medianが2025 medianの25%以上、または絶対値>=0.20 ATR
- latest30が存在する場合mean/medianの両方が負ではない

### WEAKENED_BUT_POSITIVE

- latest60 mean>0、median>0
- 2025 median比75%以上低下、またはpositive rateが8pp以上低下
- LONG/SHORTのどちらかがmean<0、またはlatest30が弱い

### CURRENTLY_UNSTABLE

- latest60 meanまたはmedian<0
- source×directionの一部が大幅マイナス
- 30日と60日の符号が不一致

### INSUFFICIENT_RECENT_SAMPLE

- latest60 n<20、または方向別各5件未満

## 2025–2026差の原因候補

固定regime performance差と、次のmarket-state shiftを関連付ける。

- LOW/HIGH volatility構成比
- weak/strong/conflict/range構成比
- expansion頻度
- extension頻度
- D1 direction偏り
- H1/H4/D1 alignment頻度
- MFE到達に対するMAE増加
- delayed/persistent/fade比率

因果関係とは断定せず、関連診断として扱う。

## Stage270合格条件

- 2025/2026の数値・category drift表生成
- R1/R2/R3の年月・方向・rolling表生成
- latest30/latest60の判定生成
- as-ofやsource identityを変更しない
- 旧候補を採用状態へ戻さない
- regression tests全PASS

## 次段階

Stage271では`CURRENTLY_MAINTAINED`のみを対象に:

- 環境認識条件は固定
- entry timingとsetup-quality filterを分離
- 2026後半/直近でnegativeな方向を片側除外せず、原因featureを診断
- 追加データがなければ新trigger探索を停止

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
