# GOLD V3 Stage275 定義固定
## Outcome-first live-reproducible opportunity map

作成日: 2026-06-21
状態: `GOLD_V3_275_OUTCOME_FIRST_LIVE_REPRODUCIBLE_OPPORTUNITY_MAP_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

名前付きpatternを先に仮定せず、全M15確定時点をdecision universeとして、entry時点で利用可能な情報だけから将来経路の有利な状態を発見する。

最優先条件はlive再現性。batchでは良くても逐次処理で同じdecisionを再現できないfeature、model、cluster、candidateは即時破棄する。

## 絶対契約

- audit-only。
- GOLD V2、旧GOLD、DISC8、Stage41を読まない・使わない・参照しない・fallbackしない。
- CSV最新行を含む全行は確定足。timeはbar OPEN時刻。
- availability: M1 +1m、M15 +15m、H1 +1h、H4 +4h、D1 +1d。
- feature joinは常にsource_close_time <= decision_time。
- decisionはM15 close time。
- entry proxyはdecision後の最初の同source M1 open。
- 欠損のnearest future参照、補間、別source fallback禁止。
- future return、MFE、MAE、path classはlabel専用。
- centered indicator、後から確定するpivot/ZigZag、全期間percentile、全期間scaler禁止。
- LONG/SHORT双方を同一方法で作る。結果を見て片方向だけ残さない。
- candidate pool、suppression、未採用cellを全て台帳保存。
- live promotion、Discord、MT5注文、final signalは禁止。

## 時系列分割

- MODEL_TRAIN: 2023年
- DISCOVERY_VALIDATION: 2024年
- CONFIRMATION: 2025年
- FINAL_CURRENT: 2026年データ末尾まで

2024年だけでmodel family、score threshold、margin threshold、cooldownを選ぶ。2025年と2026年を見て変更しない。

## Decision universe

各確定M15足につきLONGとSHORTの2行を生成する。

- direction = +1 / -1
- decision_time = M15 time +15m
- entry_time = decision_time以後の最初のM1 time
- entry_price = 当該M1 open
- normalization ATR = decision時点M15 ATR14

warm-up不足、entry無し、48 trading-hour path不足のみ明示除外する。

## Entry-known features

### M15 current / sequence

- signed return 1/4/8/16/32 bars divided by ATR14
- ATR14/price、ATR14/ATR50、ATR14 slope8
- range/ATR、signed body/ATR、body/range、close position、upper/lower wick/range
- EMA20/50/200 distance divided by ATR14
- EMA20/50 slope4 divided by ATR14
- rolling high20/low20 distance
- realized volatility 16/64 ratio
- range compression 4/32
- up-bar share8、new-high count16、new-low count16

方向性featureはcandidate directionへalignmentしてLONG/SHORT共通表現にする。非方向featureはそのまま使う。

### H1 / H4 / D1 closed context

各時間足で、decision時点までに確定した最後の足のみ使用:

- return 1/4/8 bars / ATR
- ATR/price、ATR14/ATR50
- EMA20/50/200 distance / ATR
- EMA20/50 slope
- close position in rolling20 range
- range/ATR、signed body/ATR

### Calendar/session

- broker-server hour sin/cos
- day-of-week sin/cos

時間帯を後付けfilterには使わず、model入力またはdiagnosticだけに使う。

## Labels

各directionについてM1経路から:

- terminal return: 8h / 24h / 48h in ATR
- MFE / MAE: 8h / 24h / 48h
- `FF1_24H`: +1ATRが-1ATRより先。same M1成立時は adverse-first。
- `POS24`: 24h terminal return >0
- `CLEAN1_24H`: FF1_24Hかつ+1ATR到達前MAE >= -0.5ATR
- first-hit minute to +0.5/+1.0/-0.5/-1.0ATR
- path class: EARLY_FAVORABLE / DELAYED / FADE / EARLY_FAIL / MIXED

## Regime router

2023年のH1/H4/D1 contextだけでStandardScalerとKMeans(k=6, random_state=275)をfitし固定する。

- cluster idは説明変数として使用可能。
- 2024以降にcluster中心を更新しない。
- cluster単独で方向を決めない。

## Model families

同じdirection-aligned feature setで以下を事前固定比較する。

1. `LR_GLOBAL`
   - StandardScaler + LogisticRegression(C=0.25, class_weight=balanced, max_iter=2000)
2. `HGB_GLOBAL`
   - HistGradientBoostingClassifier(max_leaf_nodes=7, max_iter=120, learning_rate=0.05, min_samples_leaf=200, l2_regularization=1.0)
3. `HGB_ROUTED`
   - regime cluster別HGB。2023 train n<1500のclusterはHGB_GLOBALへfallback。

各familyで2modelをfit:

- quality model: FF1_24H
- direction model: POS24

score:

`score = 0.65 * p(FF1_24H) + 0.35 * p(POS24)`

## Candidate construction

同一decision_timeのLONG/SHORT scoreを比較する。

- higher directionのみ候補
- score thresholdは2023 train score分布のquantile q=0.85/0.90/0.95
- LONG/SHORT score margin threshold = 0.02/0.05/0.10
- cooldown = 4h / 8h / 16h（取引M1時間）

3 model families × 3 quantiles × 3 margins × 3 cooldowns = 81 fixed cells。

cooldownはdirectionに関係なく1ポジション想定のfirst-come suppression。全raw candidateとsuppressed candidateを保存する。

## 2024 discovery selection

各cellを固定1ATR SL / 1.5ATR TP / 24 trading-hour capで評価する。

same M1でSL/TP成立時はSL優先。gap-through stopは不利なM1 openを使用する。

`DISCOVERY_LEAD`必須条件:

- independent n >= 100
- LONG/SHORT各 n >= 30
- active months >= 9
- cost2 expectancy > 0
- PF cost2 >= 1.15
- median R > 0
- LONG/SHORT双方 mean R >= 0
- top5 profit share <= 50%
- prefix feature parity PASS
- batch/stream candidate parity exact

選択順位:

1. min(LONG expectancy, SHORT expectancy)
2. cost2 expectancy
3. PF
4. n

最大3cell。ただしcandidate timestamp overlap >70%のcellは下位を除く。

## 2025 confirmation

固定cellを変更せず:

- n >= 50
- cost2 expectancy >0
- PF >=1.10
- median R >=0
- LONG/SHORT各 n>=15かつmean R>=0
- positive months >=50%

通過cellのみ2026へ進む。

## 2026 final/current

- n >= 25
- cost2 expectancy >0
- PF >=1.10
- median R >=0
- LONG/SHORT各 n>=8かつmean R>=0。未満ならINSUFFICIENT_DIRECTION_SAMPLE。
- latest60 n>=10の場合cost2 expectancy >=0
- batch/stream candidate parity exact

## Live reproducibility gates

### Prefix feature parity

少なくとも256 checkpointで、全データbatch featureと、checkpoint時点までのprefixだけを再計算した最後のfeatureを比較する。

- timestamps exact
- categorical exact
- numeric max abs diff <=1e-10
- violation 1件でも当該featureを破棄し再実行

### Batch / streaming prediction parity

固定済みfeature rowsを時系列で1行ずつmodelへ渡し、score、direction選択、threshold、cooldownを逐次適用する。

batchとstreamingで:

- candidate count exact
- decision_time exact
- direction exact
- score max abs diff <=1e-12
- entry_time exact
- suppression exact

不一致cellは成績に関係なく不合格。

## 正式分類

- `LIVE_REPRODUCIBLE_MULTI_PERIOD_RESEARCH_LEAD`
- `DISCOVERY_LEAD_FAILED_2025`
- `CONFIRMED_FAILED_2026`
- `NO_DISCOVERY_LEAD`
- `LIVE_PARITY_REJECTED`
- `INSUFFICIENT_SAMPLE`

研究は停止しない。leadが無ければ、失敗原因を保持して次の探索軸へ進む。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
