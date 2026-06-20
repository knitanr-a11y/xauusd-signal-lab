# GOLD V3 Stage266D 定義固定
## Win-rate-first family-specific loss-pruning gate

作成日: 2026-06-21
状態: `GOLD_V3_266D_WINRATE_FIRST_FAMILY_GATE_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

Stage266Bのfamily別モデルを維持しつつ、閾値選択を期待値最大から勝率優先へ変更する。負け数を減らして勝率を上げ、過度に取引数を削らないgateを月次walk-forward OOFで評価する。

## 絶対契約

- Stage266Bの因果・feature selection・モデル契約を継承。
- 当月より前にexit済みの同family tradeだけで学習。
- 当月outcomeを閾値選択に使わない。
- fixed adverse ruleは使わない。
- raw candidate、accepted、rejectedを全件保存。
- LONG only、SHORT only、年別除外禁止。

## model

- family別elastic-net logistic regression
- Stage266Bと同じtraining-only stable feature selection
- target=`cost2_pnl > 0`
- cost5はstress評価として別集計

## threshold selection

training prediction retention候補:

- 30%
- 40%
- 50%
- 60%
- 70%
- 80%

training内で次を満たす候補から、retention最大を選ぶ。

1. cost2 win rate >= 60%
2. cost2 expectancy > 0
3. cost5 expectancy > 0
4. minimum accepted 20trade

該当がない場合:

- retention 35%以上に最も近い候補のうちcost2 win rate最大
- 同点はcost5 expectancy最大
- さらに同点はretention最大

## OOF評価

familyごとに:

- raw OOFとaccepted/rejectedを比較
- cost2 win rate改善幅
- cost5 win rate改善幅
- expectancy/PF
- retention
- source別
- direction別
- top5 profit concentration

## family合格基準

- accepted 25件以上
- retention 30〜80%
- cost2 win rate >= 60%
- cost2 win rateがrawより5 percentage point以上改善
- cost5 win rate >= 55%
- cost5 expectancy > 0
- cost5 PF >= 1.25
- rejected expectancy < accepted expectancy
- 2025/2026両sourceでaccepted expectancy >= 0
- LONG/SHORT各10件以上かつaccepted expectancy >= 0
- top5 positive profit share <= 60%

## 解釈

取引数を極端に削って100%勝率に見せることは禁止。勝率、retention、期間安定性、方向安定性を同時に要求する。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
