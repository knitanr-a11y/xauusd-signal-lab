# GOLD V3 Stage266A Loss-pruning first pass

作成日: 2026-06-21

状態: `GOLD_V3_266A_LOSS_PRUNING_FIRST_PASS_PARTIAL_AUDIT_ONLY`

## 方針

個別の負けtradeを後から削除せず、pending注文作成時点で既知の特徴だけを使い、月次expanding walk-forwardで予測下位30%を除外した。

全raw candidateとGATE_ACCEPTED / GATE_REJECTEDは台帳に残した。

## C1 H4 six-bar channel

OOF全体:

- 95 resolved
- cost2 win rate 53.68%
- cost2 expectancy +3.461 USD/oz
- cost2 PF 1.345
- cost5 expectancy +0.461
- cost5 PF 1.040

Gate accepted:

- 61 resolved、retention 64.21%
- cost2 win rate 59.02%
- cost2 expectancy +7.205
- cost2 PF 1.805
- cost5 win rate 54.10%
- cost5 expectancy +4.205
- cost5 PF 1.408

Gate rejected:

- 34 resolved
- cost2 win rate 44.12%
- cost2 expectancy -3.257
- cost2 PF 0.727
- cost5 expectancy -6.257
- cost5 PF 0.543

C1では、gateが負け側を分離する方向へ機能した。

## C2 H4 pullback

- accepted 37件、cost2 win rate 56.76%、期待値+4.904
- rejected 17件、cost2 win rate 58.82%、期待値+8.111

現在の共通gateは良いtradeをより多くrejectしており失敗。C2専用gateが必要。

## C3 H4 compression

- accepted 21件、cost2 win rate 52.38%、期待値+11.900
- rejected 9件、cost2 win rate 77.78%、期待値+21.448

現在の共通gateは逆方向。C3へ適用しない。

## 初回stacked portfolio

- 56 resolved
- cost2 PnL +362.59
- cost2 expectancy +6.475
- cost2 PF 1.739
- cost2 win rate 62.50%
- cost5 PnL +194.59
- cost5 expectancy +3.475
- cost5 PF 1.345
- cost5 win rate 55.36%
- 月間trade中央値 2件

勝率はcost2で改善したが、取引頻度とcost5勝率は不足。完成候補ではない。

## 判断

- C1はloss-pruning候補として残す。
- C2/C3へ共通gateを適用しない。
- 次はfamily別に負けパターンを抽出し、それぞれ別gateを作る。
- setupごとに勝率改善が確認できたものだけをstackへ追加する。
- 2025/2026は既知期間なので、OOF改善は開発結果でありlive validationではない。

運用状態: `NO_LIVE_PROMOTION_AUDIT_ONLY`
