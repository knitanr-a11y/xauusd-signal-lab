# GOLD V3 Stage263 研究設計リセット監査
## 2026年6月 contaminated pseudo-holdout

作成日: 2026-06-20  
正式状態: `GOLD_V3_263_JUNE_PSEUDO_HOLDOUT_REJECTED_AUDIT_ONLY`

## 1. 結論

手作業のsetup探索を停止し、M15確定時点の60分後returnをRidgeとHistGradientBoostingで予測し、両modelが同方向かつ開発OOF予測強度の上位15%だけを取引する設計へ切り替えた。

結果は不採用。

- 開発walk-forward OOFの予測相関: Pearson `-0.0477`、Spearman `0.0059`。
- OOF model: 304 trades、cost2 expectancy `-2.156`、PF `0.807`。
- 6月pseudo-holdout: 8 trades、cost2 expectancy `-8.195`、PF `0.185`、PnL `-65.56`。
- 6月LONG 6件・SHORT 2件の両方が赤字。
- prefix feature/prediction parity: 12/12 PASS。

この結果は、setup定義の問題だけではなく、現在のOHLC・bar tick_volume・spread・時間特徴から60分後方向を安定予測できていないことを示す。

## 2. 結果前に固定した契約

定義コミット:

`10ac0ae8b8d8b649d373fce123c9e1b3094bf078`

- 開発: 2025-01-02〜2026-05-31。
- expanding monthly walk-forward: 2025-07〜2026-05。
- pseudo-holdout: 2026-06-01〜2026-06-19。
- decision: 完了M15、entryはdecision_time exact M1 OPEN。
- exit: 60分後exact M1 OPEN。
- cost: 2 USD。
- safe window: 平日UTC 08:00以上18:00未満。
- one-active: 保有中の新規tradeを抑制。
- E2〜E8は直接ruleにもfeatureにも使用しない。
- 6月をfeature、model、threshold、方向選択に使用しない。

## 3. model

### Ridge

- median impute
- standardize
- alpha 10

### HistGradientBoosting

- learning rate 0.05
- max iter 200
- max depth 3
- max leaf nodes 15
- min samples leaf 100
- L2 1.0

予測targetは60分後gross returnをM15 ATR14で正規化した値。

ensemble USD予測は2 modelの平均。両modelの符号一致を必須とした。

## 4. frozen threshold

開発OOFの符号一致sampleにおけるabs ensemble prediction 85 percentile:

`3.361803 USD`

3 USD floorより大きかったため、frozen thresholdは同じく:

`3.361803 USD`

6月結果を使ったthreshold変更はしていない。

## 5. 開発walk-forward OOF

対象予測行: 9159

- MAE: 10.504 USD
- RMSE: 18.913 USD
- Pearson: -0.0477
- Spearman: 0.0059

model trade:

- count: 304
- PnL: -655.32
- expectancy: -2.156
- PF: 0.807
- max DD: 1322.90

OOFは2025年10月・2026年1月など一部月で利益があったが、2026年3月だけで約-1,012 USDとなり、全体edgeは負だった。予測値と実現returnの順位相関もほぼゼロだった。

OOF方向診断:

- LONG: 118件、PnL -802.69、expectancy -6.802
- SHORT: 186件、PnL +147.37、expectancy +0.792

ただしSHORTのみへの変更はOOF結果確認後の後付けになるため禁止。また6月SHORTも赤字だった。

## 6. 6月pseudo-holdout

eligible M15 decisions: 600

prediction:

- MAE: 10.181 USD
- RMSE: 14.317 USD
- Pearson: -0.1034
- Spearman: -0.0497

20 raw signalsのうちone-active後は8 trades。

| direction | count | cost2 PnL | expectancy |
|---|---:|---:|---:|
| LONG | 6 | -49.82 | -8.303 |
| SHORT | 2 | -15.74 | -7.870 |
| ALL | 8 | -65.56 | -8.195 |

PFは`0.185`、勝率25%。

最大損失は2026-06-05 16:00 LONGの-42.79 USD。モデルは+4.34 USDを予測したが、実際の60分returnは-40.79 USDだった。

## 7. baseline比較

| strategy | trades | cost2 PnL | expectancy | PF |
|---|---:|---:|---:|---:|
| MODEL | 8 | -65.56 | -8.195 | 0.185 |
| ALWAYS LONG | 150 | -522.66 | -3.484 | 0.488 |
| ALWAYS SHORT | 150 | -77.34 | -0.516 | 0.904 |
| PREV BAR DIRECTION | 150 | -221.30 | -1.475 | 0.745 |
| EMA TREND | 150 | -252.82 | -1.685 | 0.717 |

model PnLはbaselineよりわずかに小さい損失だったが、trade数を8件まで減らしたためである。expectancyとPFは全baselineより悪く、方向予測edgeとは認定しない。

## 8. 事前合否

| criterion | result |
|---|---|
| trade count >= 15 | FAIL |
| cost2 expectancy > 0 | FAIL |
| PF >= 1.10 | FAIL |
| PnL above all baselines | PASS |
| max DD <= gross profit | FAIL |
| upper-confidence expectancy >= lower | PASS |
| single positive trade share <= 50% | FAIL |
| prefix feature/prediction parity | PASS |

8項目中4項目を失敗したためREJECT。

上位confidence半分もexpectancy -5.28 USDであり、confidenceが高ければ利益になる関係は確認できなかった。positive PnLの88.2%を1 tradeが占めた。

## 9. 判定

`JUNE_PSEUDO_HOLDOUT_REJECTED`

- setup探索型: 不採用済み。
- 単純な意思決定回帰型: 不採用。
- 現在のbar dataで60分方向を自動売買に使えるedge: 未証明。
- threshold緩和、SHORT限定、別時間帯、別horizonを同じ6月で再探索することは禁止。

この結果後に同じデータで別modelを連続探索すると、6月pseudo-holdoutも完全に開発データ化する。したがって現在データだけを使う方向性自動売買研究はここで停止する。

## 10. 実用的な選択肢

現在データを活用するなら、次のいずれかへ目的を変更する。

1. 方向を出さず、将来値幅・高volatility発生だけを予測するalert。
2. directionは裁量または別情報源に任せ、modelは取引禁止・size縮小・activity alertだけを担当する。
3. tick/bid-askまたは外部市場を追加して、完全に新しいfuture holdoutで再開する。

現在の6月を再び合否判定に使用しない。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
