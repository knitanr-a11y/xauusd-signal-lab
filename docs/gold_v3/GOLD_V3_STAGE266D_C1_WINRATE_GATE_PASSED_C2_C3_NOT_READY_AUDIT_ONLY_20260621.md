# GOLD V3 Stage266D Win-Rate-First Family Gate Audit

作成日: 2026-06-21

正式状態: `GOLD_V3_266D_C1_WINRATE_GATE_PASSED_C2_C3_NOT_READY_AUDIT_ONLY`

## 方法

- family別に独立したelastic-net logistic gate
- feature selectionも各月のtraining内だけ
- targetはcost2勝ち/負け
- trainingでcost2勝率60%以上、cost2/cost5期待値プラスを満たす最大retentionを選択
- 当月へ固定適用
- 月次expanding walk-forward OOF
- entry-known情報だけを使用
- raw/rejectedを削除せず台帳保存

## C1 H4 six-bar channel

### RAW OOF
- 74件
- cost2勝率 52.70%
- cost2期待値 +4.322
- cost5勝率 48.65%
- cost5期待値 +1.322
- cost5 PF 1.114

### Gate accepted
- 52件
- retention 70.27%
- cost2勝率 61.54%
- cost2期待値 +11.225
- cost2 PF 2.483
- cost5勝率 57.69%
- cost5期待値 +8.225
- cost5 PF 2.075
- top5 positive profit share 40.07%

### Gate rejected
- 22件
- cost2勝率 31.82%
- cost2期待値 -11.994
- cost5勝率 27.27%
- cost5期待値 -14.994
- cost5 PF 0.279

### Stability
2025 source:
- accepted cost2勝率67.74%
- accepted cost5期待値+6.477

2026 source:
- accepted cost2勝率52.38%
- accepted cost5期待値+10.806

LONG:
- 38件、cost2勝率63.16%、cost5期待値+5.506

SHORT:
- 14件、cost2勝率57.14%、cost5期待値+15.607

C1は事前基準11/11 PASS。

重要:
- 2026勝率は60%未満だが期待値はプラス
- 全体60%超えを確認したが、future validationではない

## C2 H4 pullback

### Gate accepted
- 25件
- retention 65.79%
- cost2勝率64.00%
- cost2期待値+6.119
- cost5勝率52.00%
- cost5期待値+3.119
- cost5 PF1.410

勝率は改善したが:
- cost5勝率55%未満
- top5 positive profit share 60.08%
で2基準FAIL。

C2はnear-pass。負けの数は減ったが、利益が少数tradeに寄り、cost stress時の勝率が不足。

## C3 H4 compression

### Gate accepted
- 15件
- retention78.95%
- cost2勝率66.67%
- cost5勝率60.00%
- cost5期待値+20.976
- cost5 PF7.529

ただしraw OOF cost2勝率73.68%から低下。accepted15件、方向別件数不足、top5利益依存84.16%。

C3は元候補自体が強い可能性があるが、現在のgateは負け削減に成功していない。gateを掛けずにsample蓄積対象とする。

## 正式判断

- C1: loss-pruning componentとして残す
- C2: 専用改善を継続
- C3: gateを止め、raw candidateの追加観測を優先
- fixed hard veto: 不採用
- stackへ即時live投入: 禁止

## 次の積み上げ

1. C1 acceptedを第一componentとして固定
2. C2のcost5勝率・利益集中を改善
3. C3は件数蓄積まで無理に削らない
4. 新family C4を追加
5. family単体で改善確認後にfirst-come stack
6. portfolio全体で月間trade数と勝率を再監査

## 注意

2025/2026は既知期間であり、今回のOOFは開発内の時系列外部評価。live validationではない。

運用状態: `NO_LIVE_PROMOTION_AUDIT_ONLY`
