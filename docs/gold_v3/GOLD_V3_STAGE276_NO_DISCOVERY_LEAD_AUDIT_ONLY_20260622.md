# GOLD V3 Stage276 Sequence and State Transition Discovery Audit

作成日: 2026-06-22  
正式状態: `GOLD_V3_276_NO_DISCOVERY_LEAD_AUDIT_ONLY`

## 結論

Stage275のstatic snapshot cellを再調整せず、sequence、finite-state transition、月次walk-forward model、3種類の明示event patternを別ベクトルとして評価した。

結果:

- M15 decision times: 81,781
- LONG/SHORT direction-expanded rows: 163,562
- sequence/state features: 48
- model cells: 32
- event cells: 80
- total fixed cells: 112
- 2024 discovery lead: 0
- 2025 confirmationへ進んだcell: 0
- 2026 final cell: 0

強い候補は見つからなかった。現行Specialist Health Router V3へ追加しない。

## Live再現性

### Prefix feature parity

2024以降64 checkpointで、全期間batch featureと各checkpointまでのprefix再計算を比較した。

- PASS: 64/64
- features: 48 × LONG/SHORT
- NaN pattern mismatch: 0
- maximum absolute difference: 0.0

### Model score parity

2 model × quality/positiveの4modelについてwhole batch、64-row chunk、1-row replayを比較した。

- PASS: 4/4
- chunk64 maximum difference: 0.0
- one-row maximum difference: 2.22e-16以下

float32では約1e-7の差が出たため正式採用せず、float64へ固定して再実行した。

### Candidate replay parity

- model candidate configurations: 16
- accepted candidate index exact: 16/16
- direction exact: 16/16

したがって不合格理由はlive再現不能ではなく、2024でedgeが無かったこと。

## Sequence model結果

2024最上位cell:

`SGD_A5E4_Q95_M03_C4H_WIDE_225_40_3H`

- n=98
- win rate=58.16%
- cost0.60 mean=-0.315 USD/oz
- cost0.60 PF=0.831
- cost1.00 PF=0.649
- median gross R=+1.054
- LONG n=38、mean=+0.285 USD/oz
- SHORT n=60、mean=-0.695 USD/oz
- top5 positive-profit share=20.9%

medianはプラスだが、大きい損失側が合計をマイナスへ押し下げた。SHORT側が明確に不安定で、両方向契約を満たさない。

固定したまま診断すると:

- 2025: n=17、mean=-3.144、PF=0.503
- 2026: n=9、mean=+14.932、PF=26.60

2026だけは非常に良く見えるがn=9であり、2025で崩れている。2026を見て方向・threshold・exitを変更して救済しない。

## Event pattern結果

### Compression → Expansion → First Retest

16 pattern × 2 exitを評価したが、2024 PF1以上の安定cellは無かった。

### Failed Breakout → Reclaim / Rejection

最良近傍:

`FBR_D05_CP65_H1_NOT_OPPOSED_WIDE_225_40_3H`

- 2024 n=394
- win rate=49.49%
- mean=-0.722
- PF=0.744
- LONG mean=-0.748
- SHORT mean=-0.696

件数は十分だがedgeが無い。

### H1 Transition → First Pullback

最良event cell:

`H1T_A16_T50_H4_ALIGNED_FAST_15_10_8H`

- 2024 n=163
- win rate=39.26%
- mean=-0.533
- PF=0.750
- LONG mean=-0.326
- SHORT mean=-0.852

上位足transition自体はcandidate母集団を作るが、entry edgeにはならなかった。

## 根本原因

1. **Direction asymmetry**
   - 最上位model cellはLONGが小幅プラス、SHORTがマイナス。
   - 結果を見てSHORTだけ除外することは契約違反なので行わない。

2. **Positive median / negative expectancy**
   - wide exitでmedianはプラスでも、少数の大きい逆行が合計をマイナスにした。

3. **2025 generalization failure**
   - 2024近傍cellは2025でさらに悪化した。

4. **2026 regime trap**
   - 一部cellは2026少数例で非常に高く見えるが、2024 discoveryと2025 confirmationを通っていない。

5. **Handcrafted event families also failed**
   - modelだけでなく、compression/retest、failed breakout、H1 transitionも独立に不合格。

## 正式判断

- Stage276 sequence/state engineはlive再現可能。
- 112固定cellから2024 discovery leadは0。
- threshold緩和、片方向除外、2026だけの採用、exit後付け最適化を行わない。
- 現行Specialist Health Router V3を変更しない。
- phase2 HV retest SHADOWもACTIVE化しない。
- candidate poolの台帳は保持する。
- live promotionは禁止。

## 次の探索軸

OHLC内部のsequenceをさらに細分化する限界が強くなった。

次は、同じ価格系列の閾値探索ではなく、entry時点で取得可能な別情報源の可用性を先に監査する。

推奨Stage277:

`GOLD_V3_277_EXTERNAL_CAUSAL_CONTEXT_DATA_AVAILABILITY_AUDIT_ONLY`

優先候補:

- XAGUSD
- USDJPY / EURUSD
- US500 / NAS100等のrisk proxy
- brokerで取得可能なUSD index proxy
- 金利・実質金利proxy
- 経済指標calendar/event proximity

まず同一broker・同一server時刻・同期間の履歴が実際に取得可能かをinventory化し、取得不能なsourceを推測で使わない。

運用状態: `NO_LIVE_PROMOTION_AUDIT_ONLY`
