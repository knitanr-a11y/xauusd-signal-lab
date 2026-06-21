# GOLD V3 Stage275 Outcome-First Live-Reproducible Opportunity Map Audit

作成日: 2026-06-21  
正式状態: `GOLD_V3_275_NO_DISCOVERY_LEAD_LIVE_REPRODUCIBLE_AUDIT_ONLY`

## 結論

全M15確定時点をdecision universeとし、各時点にLONG/SHORTの2方向を置いて、entry-known featureだけから次を別々に予測した。

- 24 trading-hour以内に+1ATRが-1ATRより先に到達するか
- 24 trading-hour終点がcandidate方向へプラスか

96個のcausal numeric feature、固定6-regime router、3 model family、3 score quantile、3 direction margin、3 cooldownを組み合わせた81固定セルを評価した。

結果:

- decision times: 80,995
- direction-expanded rows: 161,990
- 2024 discovery cells: 81
- live feature parity: PASS
- live model score parity: PASS
- batch/stream candidate parity: 81/81 PASS
- `DISCOVERY_LEAD`: 0
- 2025へ昇格したcell: 0
- 2026最終判定cell: 0

今回の不合格原因はlive再現不能ではない。2023年で学習したfeature-outcome関係が2024年へ一般化せず、固定trade skeletonのコスト後期待値も全cellでマイナスだった。

## Live再現性

### Prefix feature parity

全データbatch featureと、各checkpointまでのprefixだけを使って再計算したfeatureを256時点で比較した。

- checkpoints: 256
- PASS: 256
- numeric features: 96
- maximum absolute difference: 0.0
- future-source join violation: 0

M15/H1/H4/D1のrolling、EMA、ATR、確定足as-ofはprefix invariantだった。

### Model score parity

2024年で最も広い候補条件（2023 score Q85以上、margin 0.02以上）に該当する全潜在候補行を再予測した。

| Model | Potential decisions | Rows checked | Chunk replay max diff | One-row sample max diff |
|---|---:|---:|---:|---:|
| LR_GLOBAL | 11,528 | 23,056 | 0.0 | 3.33e-16 |
| HGB_GLOBAL | 7,193 | 14,386 | 0.0 | 0.0 |
| HGB_ROUTED | 4,460 | 8,920 | 0.0 | 0.0 |

各modelで1,000行を1行ずつ予測した結果も一致した。

### Candidate replay parity

81cellすべてについて、batch constructionと時系列1decisionずつのstreaming replayを比較した。

- raw candidate count exact: 81/81
- decision time exact: 81/81
- direction exact: 81/81
- accepted candidate exact: 81/81
- cooldown suppression exact: 81/81
- score max absolute difference: 0.0

したがって今回のcandidate engineはlive実装可能な契約を満たす。

## Model generalization

### LR_GLOBAL

| Year | FF1 quality AUC | 24h direction AUC |
|---|---:|---:|
| 2023 train | 0.555 | 0.637 |
| 2024 discovery validation | 0.533 | 0.545 |
| 2025 | 0.514 | 0.580 |
| 2026 | 0.521 | 0.528 |

線形modelはわずかなOOS rankingを残したが、trade可能な強度には届かなかった。

### HGB_GLOBAL

| Year | FF1 quality AUC | 24h direction AUC |
|---|---:|---:|
| 2023 train | 0.667 | 0.878 |
| 2024 discovery validation | 0.516 | 0.538 |
| 2025 | 0.497 | 0.449 |
| 2026 | 0.497 | 0.486 |

2023年内では高く見えたが、2024年でほぼrandomまで低下した。

### HGB_ROUTED

| Year | FF1 quality AUC | 24h direction AUC |
|---|---:|---:|
| 2023 train | 0.797 | 0.962 |
| 2024 discovery validation | 0.503 | 0.511 |
| 2025 | 0.494 | 0.454 |
| 2026 | 0.515 | 0.501 |

regime別modelはtrain内performanceを最も高めたが、外部年へ最も一般化しなかった。固定snapshot featureとrouterを細分化すると、2023年固有関係を学習したと判断する。

## 2024 discovery grid

81cell中、正式基準を通過したcellは0。

### 最上位cell

`LR_GLOBAL_Q85_M02_C16H`

- n=288
- LONG 250 / SHORT 38
- mean gross R +0.189
- median gross R -1.000
- cost2 expectancy -1.345 USD/oz
- PF cost2 0.484
- LONG mean +0.190R
- SHORT mean +0.184R
- top5 profit share 10.9%

Gross平均はプラスだが、典型tradeはSLである。M15 ATRに対して2 USD costが大きく、cost後は明確なマイナスとなった。また候補の86.8%がLONGで方向バランス基準を満たさない。

### 最上位HGB cell

`HGB_GLOBAL_Q95_M02_C16H`

- n=99
- LONG 44 / SHORT 55
- mean gross R +0.186
- median gross R -1.000
- cost2 expectancy -1.406 USD/oz
- PF cost2 0.512
- LONG mean +0.307R
- SHORT mean +0.090R

方向件数は比較的均衡したが、n<100、中央値-1R、cost後マイナス、PF<1だった。

全cellで:

- cost2 expectancy >0: 0
- PF cost2 >=1.15: 0
- median R >0: 0
- `DISCOVERY_LEAD`: 0

## 近接cellの期間診断

正式選択cellが無いため、上位10cellを診断目的だけで2025/2026へ変更なしで適用した。

- 上位10cellは2025年ですべてcost後マイナス
- HGB上位cellは2026年もcost後 -4.28〜-4.82 USD/oz
- LR 16h cellは2026年 cost後 -1.52 USD/oz
- LR 4h cellだけ2026年全体が +0.002 USD/ozとほぼゼロだったが、latest60は -2.22 USD/oz
- いずれもmedian Rは-1.0

固定thresholdの近傍に、見逃したmulti-period leadは確認できなかった。

## Regime opportunity map

regime routerは2023年だけでfitし、以降更新しなかった。

regime mixは大きく変化した。

- Regime 1 share: 2023 18.9% → 2025 5.3% → 2026 0%
- Regime 5 share: 2023 23.0% → 2024 37.2% → 2026 46.1%
- Regime 4 share: 2023 9.1% → 2025 29.8% → 2026 26.6%

診断上:

- Regime 3 LONGは2023〜2025年で24h平均・中央値がプラスだったが、2026年平均は-0.650ATRへ反転
- Regime 4 LONGは4年すべて平均プラスだったが、2023年中央値は-0.398ATRで、SHORT側は安定しない
- Regime 1 LONGは2023〜2025年で強かったが、2026年には同clusterが出現しなかった

単一regime IDをsignalへ変換できる、両方向・複数年安定clusterは無かった。

## 根本原因

1. **Static nonlinear overfit**  
   HGB_ROUTED direction AUCは2023年0.962から2024年0.511へ低下した。

2. **Path-quality ranking不足**  
   2024年FF1 AUCはLR 0.533、HGB 0.516、routed 0.503。初期逆行の小さい経路を十分に識別できない。

3. **Typical trade loss**  
   上位cellでも中央値は-1R。少数TPがgross平均をプラスにするが、安定edgeではない。

4. **Cost fragility**  
   gross Rは小幅プラスでも、2 USD/oz stress後に全cellがマイナス。

5. **Direction concentration**  
   LR上位cellはLONGへ偏り、両方向routerになっていない。

6. **Regime identity is insufficient**  
   clusterの分布・方向関係が年ごとに変わり、cluster IDだけでは状態遷移を説明できない。

## 正式判断

- Stage275のfeature、model score、candidate replayはlive再現可能。
- live parityを満たすことと、edgeが存在することは別である。
- 2023年のstatic feature関係は2024年へ十分一般化しなかった。
- 81cellからresearch leadは作れなかった。
- threshold緩和、2026年だけの方向選択、cost除外による救済は行わない。
- GOLD研究は停止しない。

## 次の探索軸

次は `GOLD_V3_276_SEQUENCE_AND_STATE_TRANSITION_DISCOVERY_AUDIT_ONLY`。

Stage275の失敗から、現在値snapshotではなく状態変化を主対象にする。

- M15直近32〜64本の順序情報
- volatility compression → expansion transition
- H1/H4 direction transition
- regime滞在時間とcluster遷移
- session開始後のpath sequence
- favorable/adverse excursionの早期予測
- expanding monthly walk-forward training
- liveで更新可能なstateful sequence encoder

batch/stream hidden-state parityを最初に通し、その後に探索する。研究は継続するが、Stage275の不合格cellは再利用しない。

## Correctness

- forbidden legacy sources: not read
- prefix feature parity: 256/256 PASS
- model score parity: PASS
- candidate replay parity: 81/81 PASS
- future labels excluded from feature set
- 2025/2026 not used for discovery selection
- same-bar SL priority
- all candidate and suppression ledgers retained
- regression tests 4/4 PASS
- live promotion prohibited

運用状態: `NO_LIVE_PROMOTION_AUDIT_ONLY`
