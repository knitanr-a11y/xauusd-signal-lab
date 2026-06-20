# GOLD V3 Stage266A handoff

状態: `GOLD_V3_266A_LOSS_PRUNING_FIRST_PASS_PARTIAL_AUDIT_ONLY`

## 合意した開発方針

1. raw candidateは削除せず全件台帳へ残す。
2. 負けtradeの共通点をentry-known特徴へ変換する。
3. 月次walk-forward OOFでgateを評価する。
4. gateで勝率・期待値が改善したcandidate familyだけを残す。
5. 別candidate familyも同じ手順で改善する。
6. 改善済みfamilyだけをportfolioへstackする。

## Stage266A結果

C1 H4 six-bar channel:
- OOF全95件: cost2 WR53.68%、exp+3.461、PF1.345
- gate accepted61件: cost2 WR59.02%、exp+7.205、PF1.805
- gate rejected34件: cost2 WR44.12%、exp-3.257、PF0.727

C1 gateは負け削減として機能。

C2 pullback / C3 compression:
- 共通gateは良いtradeを削ったため不採用。
- family専用gateを作る。

初回stack:
- 56 trades
- cost2 WR62.50%、exp+6.475、PF1.739
- cost5 WR55.36%、exp+3.475、PF1.345
- 月間中央値2件

まだ頻度不足。

## 次

Stage266B:
- C1専用gate refinement
- C2専用loss gate
- C3専用loss gate
- 新候補C4を追加
- family単体で基準を通ったものだけstack

運用: `NO_LIVE_PROMOTION_AUDIT_ONLY`
