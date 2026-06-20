# GOLD V3 Stage268 Forward Distribution / Regime Diagnostic

作成日: 2026-06-21  
正式状態: `GOLD_V3_268_FORWARD_DISTRIBUTION_AND_REGIME_DIAGNOSTIC_COMPLETE_AUDIT_ONLY`

## 結論

Stage267で作成した全H1/H4 decision pathを、時間帯、trend/range、volatility、伸び、圧縮/拡大、ローソク形状、D1/H4/H1関係、activation状態、および4〜120取引時間horizonで分解した。

- H1: 8,636 decisions
- H4: 2,257 decisions
- 基礎researchable cell: 573
- 方向偏重lead: 415
- LONG/SHORT×2025/2026の4区分まで確認した厳格cell: 12行、11構造
- 厳格cellの単独軸: 0
- 厳格cellはすべて2条件interaction

573という数字はstrategy数ではない。同じ状態を複数horizon・軸で重複集計したdistribution cellである。

## 無条件仮説の結果

### 完了足方向へのcontinuation

無条件のBAR_CONTINUATIONにはedgeがない。

- H1 48h: positive rate 50.91% / median 0.135 ATR
- H4 48h: positive rate 51.53% / median 0.107 ATR

LONG側とSHORT側の差が大きく、単純な前足方向は市場上昇biasを拾っているだけだった。

### timeframe EMA trend

- H1 48h: positive rate 54.77% / median 0.507 ATR
- H4 48h: positive rate 54.74% / median 0.280 ATR

全体ではプラスだが、2025のSHORTは負、2026のSHORTは正となり、単独では期間安定性がない。

### D1 trend

見かけ上は最も強い。

- H1 48h: positive rate 59.26% / median 1.016 ATR
- H1 72h: positive rate 59.81% / median 1.451 ATR
- H1 120h: positive rate 63.21% / median 2.895 ATR
- H4 48h: positive rate 59.40% / median 0.506 ATR
- H4 120h: positive rate 64.11% / median 1.457 ATR

ただし2025にはD1_TRENDのSHORT decisionが0件だった。したがってD1_TRENDの445 researchable cellは、下落D1 regimeを両sourceで検証した結果ではなく、2025の強い上昇相場を大きく含む。正式entry signalにはできない。

### mean reversion

無条件mean reversionは不採用方向。

- H1 48h: positive rate 45.69% / median -0.452 ATR
- H4 48h: positive rate 45.08% / median -0.294 ATR

一部の短期cellは見つかったが、source×directionの4区分安定性を満たさない。

## 厳格に残った12 cell

| TF | Direction hypothesis | 条件 | Horizon | n | Positive | Median return | MFE/MAE |
|---|---|---|---:|---:|---:|---:|---:|
| H1 | TIMEFRAME_TREND | trend_state=WEAK_TREND × volatility_bucket=LOW | 48h | 570 | 62.8% | 1.887 ATR | 1.75 |
| H1 | TIMEFRAME_TREND | hour_bin=UTC20_23 × volatility_bucket=LOW | 72h | 255 | 58.8% | 1.509 ATR | 1.76 |
| H1 | TIMEFRAME_TREND | hour_bin=UTC08_11 × volatility_bucket=LOW | 48h | 444 | 61.7% | 1.330 ATR | 1.61 |
| H1 | BAR_CONTINUATION | hour_bin=UTC08_11 × volatility_bucket=HIGH | 72h | 300 | 57.3% | 1.248 ATR | 1.54 |
| H1 | TIMEFRAME_TREND | hour_bin=UTC00_03 × volatility_bucket=LOW | 24h | 289 | 61.6% | 1.145 ATR | 1.52 |
| H1 | BAR_CONTINUATION | hour_bin=UTC08_11 × volatility_bucket=HIGH | 48h | 304 | 56.9% | 0.850 ATR | 1.56 |
| H1 | TIMEFRAME_TREND | hour_bin=UTC04_07 × volatility_bucket=LOW | 24h | 394 | 56.9% | 0.641 ATR | 1.48 |
| H4 | BAR_CONTINUATION | candle_state=STRONG_DIRECTIONAL × trend_state=CONFLICT | 48h | 111 | 59.5% | 0.421 ATR | 1.42 |
| H4 | BAR_CONTINUATION | candle_state=INDECISION × trend_state=WEAK_TREND | 12h | 59 | 62.7% | 0.330 ATR | 1.87 |
| H4 | BAR_CONTINUATION | h1_h4_d1_alignment=OPPOSED × extension_bucket=HEALTHY_EXTENSION | 12h | 113 | 58.4% | 0.297 ATR | 1.77 |
| H1 | BAR_CONTINUATION | candle_state=INDECISION × trend_state=RANGE | 8h | 231 | 57.6% | 0.246 ATR | 1.55 |
| H4 | BAR_CONTINUATION | candle_state=STRONG_DIRECTIONAL × trend_state=WEAK_TREND | 8h | 84 | 58.3% | 0.212 ATR | 1.31 |

## 主要な研究family

### A. H1 low-volatility trend continuation

最も強いcell:

- H1 WEAK_TREND × LOW volatility
- TIMEFRAME_TREND方向
- 48取引時間
- n=570
- positive rate=62.81%
- median return=1.887 ATR
- LONG/SHORT、2025/2026の各区分で平均プラス

path timing:

- PERSISTENT 35.13%
- DELAYED 23.19%
- FADE 12.61%

PERSISTENT+DELAYEDが58.32%であり、短期entryではなく2日程度のmulti-day trend familyとして研究すべき。

時間帯別low-vol trendも、UTC00-03/04-07では24h、UTC08-11では48h、UTC20-23では72hが残った。時間帯ごとに伸びるhorizonが異なる。

### B. H1 high-volatility morning continuation

- UTC08-11 × HIGH volatility
- BAR_CONTINUATION方向
- 48h / 72h
- n約300
- positive rate 56.9〜57.3%
- median 0.850〜1.248 ATR

通常のBAR_CONTINUATIONは無効だが、高volatilityかつUTC08-11に限定すると両方向・両sourceで分布差が残った。これはlow-vol trend familyとは別のmomentum family候補。

### C. H4 candle-structure continuation

H4では大規模な単独regimeより、ローソク形状とtrend状態の組合せだけが残った。

- STRONG_DIRECTIONAL × CONFLICT: 48h、n=111、positive 59.46%
- INDECISION × WEAK_TREND: 12h、n=59、positive 62.71%
- STRONG_DIRECTIONAL × WEAK_TREND: 8h、n=84、positive 58.33%
- H4/D1 OPPOSED × HEALTHY_EXTENSION: 12h、n=113、positive 58.41%

件数はH1 familyより少なく、Stage269では同一familyとしてまとめず別々に確認する。

## 重要な否定結果

1. 単独軸だけで厳格基準を満たすcellは0。
2. D1 trendは見かけ上強いが、2025にD1 SHORTがなく方向regime coverage不足。
3. timeframe trend単独はSHORTの2025/2026符号が反転。
4. mean reversion全体はマイナス。
5. observed closure後activationは失効させるべきではないが、それ自体をedgeとは扱えない。

## path timing

厳格cellの多くは即時型ではない。

- H1 low-vol weak trend: persistent+delayed 58.32%
- H1 high-vol UTC08-11 continuation: persistent+delayed 49.06%
- H4 strong-directional/conflict: persistent+delayed 54.39%

したがって、Stage269で再び8時間固定exitを置くことは禁止。familyごとに24/48/72h profileを保持する。

## correctness

- H1 own/H4/D1 feature merge coverage: 100%
- H4 own/D1 feature merge coverage: 100%
- D1 as-of violation: 0
- H1へのH4 as-of violation: 0
- normalized path finite rate: H1 99.94%、H4 99.95%
- 旧候補status: REFERENCE_ONLY_NOT_VALIDATEDを維持
- Stage268 acceptance criteria: ALL PASS

## 正式判断

Stage268でstrategyは完成していない。

残すのは次の3研究family:

1. H1 low-volatility trend continuation / multi-day
2. H1 high-volatility UTC08-11 continuation / momentum
3. H4 candle-structure continuation / short-to-medium horizon

ただし同じ2025〜2026で発見したため、entry ruleを作る前にpre-2025データで固定条件を検証する。

## 次Stage269

`GOLD_V3_269_PRE2025_COARSE_PATH_VALIDATION_AUDIT_ONLY`

- H1 family: goldsharp H1の2023-01-25〜2024-12-31
- H4 family: goldsharp H4の2020-01-01〜2024-12-31
- H1/H4 bar OHLCでcoarse forward pathを再構築
- exact M1 execution/PnLとは呼ばない
- 11固定構造の条件・horizonを変更せず検証
- 方向別・年別で符号が維持されるものだけ次へ残す

pre-2025で維持されない場合は破棄する。維持された場合だけM1履歴取得後のexact execution監査へ進む。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
