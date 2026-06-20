# GOLD V3 Stage266D handoff

正式状態:
`GOLD_V3_266D_C1_WINRATE_GATE_PASSED_C2_C3_NOT_READY_AUDIT_ONLY`

## 開発原則

- 勝ち/負けを多角的に比較
- 負けtradeを手動削除しない
- entry-known特徴だけでfamily専用gate化
- 月次walk-forward OOFのみ正式評価
- 改善familyだけstack

## C1

gate accepted 52 / raw74
- cost2 WR 52.70% -> 61.54%
- cost5 WR 48.65% -> 57.69%
- cost5 exp +1.322 -> +8.225
- cost5 PF 1.114 -> 2.075

rejected22:
- cost2 WR31.82%
- cost5 exp -14.994

C1はloss-pruning componentとして固定。

## C2

accepted25:
- cost2 WR64%
- cost5 WR52%
- cost5 exp+3.119
- PF1.410

cost5 WRとtop5集中で未合格。改善継続。

## C3

accepted15、cost2 WR66.67%だがraw73.68%より悪化。
件数・方向・利益集中で未合格。
gateを止めてraw sample蓄積。

## 深いpattern

C1:
- H4 range/body/returnとH1 ATRが同時膨張した追いかけが主要loss
C2:
- H4 trend position低位、H1 slope弱い、または大body追いがloss
C3:
- high ATR percentile、low volume、H1 streak過多がloss

固定pairwise vetoは翌月で反転したため不採用。

## 次

Stage266E:
- C1 gate frozen component
- C2専用改善
- C3 raw monitoring
- C4 new family discovery
- family合格後portfolio stacking

運用:
`NO_LIVE_PROMOTION_AUDIT_ONLY`
