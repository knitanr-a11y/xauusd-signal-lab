# GOLD V3 Stage271 Current-Regime Direction-Stability Audit

正式状態: `GOLD_V3_271_NO_STABLE_DIRECTION_GATE_R2_RECENT_ASSOCIATION_R3_LONG_INSUFFICIENT_AUDIT_ONLY`

## 結論

R2とR3の直近方向差を、entry時点で既知のH1/H4/D1特徴、勝敗差、組合せ、浅いモデル、matched control、path timingから診断した。

- R2 LONG: entry-known特徴で直近勝敗をある程度分離できたが、2025・2026前半と同じ符号で安定しない。`RECENT_REGIME_ASSOCIATION_ONLY`。
- R2 SHORT: 現在はプラスだが、過去学習modelは直近勝敗を説明できない。固定gate根拠なし。
- R3 LONG: latest60は6件だけで、全件がD1下降に逆行。`INSUFFICIENT_SAMPLE`。
- R3 SHORT: latest60は27件で強いが、entry-known modelの分離力は弱く、現在の下降regime依存が大きい。
- `STABLE_ENTRY_KNOWN_CAUSE`に該当するfeatureは0。Stage272でfilterを作る条件を満たさない。

## R2 latest60方向差

| Direction | n | Positive | Mean | Median | 8h median | 24h median | 48h median |
|---|---:|---:|---:|---:|---:|---:|---:|
| LONG | 16 | 43.75% | +1.133 | -0.397 | +0.401 | +0.682 | -0.397 |
| SHORT | 18 | 66.67% | +1.045 | +0.975 | -0.622 | +0.174 | +0.975 |

R2 LONGは平均プラスだが中央値が負で、少数の大勝に依存する。R2 SHORTは8〜12hでは逆行してから24〜48hで回復するdelayed型。

### R2 LONGの直近関連

- H1 EXPANSION: n=11、positive=54.5%、mean=+2.419
- H1 NORMAL: n=5、positive=20.0%、mean=-1.697
- H1/H4/D1 ALL_ALIGNED: n=12、median=+2.486
- ANY_RANGE: n=3、median=-1.392

直近では、明確なexpansionと上位足整合があるLONGは良く、NORMAL足・range混在は悪い。しかしこの差は過去期間で同じ強さ・符号を維持せず、固定filterにはできない。

### R2 SHORTの直近関連

- EXTREME extension: n=5、positive=40.0%、mean=-1.737
- HEALTHY extension: n=3、positive=100.0%、mean=+1.876

極端に伸びた後のSHORT impulseはfadeしやすい関連があるが、直近小標本の診断でありgate化しない。

## R3 latest60方向差

| Direction | n | Positive | Mean | Median | MFE median | MAE median |
|---|---:|---:|---:|---:|---:|---:|
| LONG | 6 | 33.33% | -0.215 | -0.506 | +0.614 | -1.718 |
| SHORT | 27 | 74.07% | +0.810 | +0.767 | +1.714 | -0.591 |

R3 LONG6件はすべてD1下降に逆行し、R3 SHORT27件はすべてD1下降と同方向だった。ただし2025ではD1上昇へ逆行したR3 SHORTもプラスだったため、D1整合は普遍原因ではなく直近regime associationである。

## Descriptive model

- R2 ALL LOGISTIC: test n=34、AUC=0.670、Brier=0.231
- R2 LONG GB: test n=16、AUC=0.794、Brier=0.331
- R2 LONG LOGISTIC: test n=16、AUC=0.730、Brier=0.338
- R2 LONG RF: test n=16、AUC=0.730、Brier=0.253
- R2 SHORT LOGISTIC: test n=18、AUC=0.528、Brier=0.277
- R3 ALL GB: test n=33、AUC=0.583、Brier=0.311
- R3 SHORT RF: test n=27、AUC=0.607、Brier=0.264

R2 LONGだけは直近勝敗をある程度分離したが、重要featureの期間安定性を満たさない。R2 SHORTとR3全体は直近勝敗のentry-known分離が弱い。

## Matched control診断

直近lossを、同regime・同方向でATR、extension、D1/H4整合、slopeが近い過去候補へ対応付けた。

| Regime | Direction | Recent loss mean | Matched past mean | Gap |
|---|---|---:|---:|---:|
| R2 | LONG | -2.714 ATR | +0.533 ATR | -3.247 ATR |
| R2 | SHORT | -4.097 ATR | +0.352 ATR | -4.449 ATR |
| R3 | LONG | -0.975 ATR | +1.462 ATR | -2.437 ATR |
| R3 | SHORT | -0.932 ATR | -1.548 ATR | +0.616 ATR |

R2とR3 LONGでは、entry時点特徴が近い過去候補はプラスだったのに、直近候補は損失になった。これは固定的な形状不良より、現在regimeで同じ形のoutcome mappingが変化した証拠である。

## Cause classification

| Regime | Direction | latest60 n | Best AUC | Classification |
|---|---|---:|---:|---|
| R2 | LONG | 16 | 0.794 | RECENT_REGIME_ASSOCIATION_ONLY |
| R2 | SHORT | 18 | 0.528 | PATH_TIMING_SHIFT_NOT_ENTRY_SEPARABLE |
| R3 | LONG | 6 | N/A | INSUFFICIENT_SAMPLE |
| R3 | SHORT | 27 | 0.607 | RECENT_REGIME_ASSOCIATION_ONLY |

## 正式判断

1. R2は現在最も維持されているが、方向divergenceを安定したentry filterで説明できない。
2. R2 LONGのexpansion/alignment差は監視featureとして残すが、gateにしない。
3. R2 SHORTはdelayed型が増えており、entryよりexit/horizon研究を優先する。
4. R3 LONGは6件しかなく、現在のD1下降に逆行したため悪化して見える。追加sampleなしで原因確定しない。
5. R3 SHORTの好成績も現在の下降regime依存が大きく、SHORT only化しない。
6. Stage272でcandidate-quality filterは作らない。R2の48h pathをexit/horizon側から研究し、R3は監視継続。

## correctness

- source/year/month/regime directionをmodel featureに使用していない。
- future return/MFE/MAEはlabelと結果診断だけに使用。
- latest60 cutoffは2026-04-20 19:00固定。
- regression tests: 4/4 PASS。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
