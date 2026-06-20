# GOLD V3 Stage266C 定義固定
## Dynamic adverse-pattern veto layered on family gates

作成日: 2026-06-21  
状態: `GOLD_V3_266C_DYNAMIC_ADVERSE_PATTERN_VETO_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

勝ち群・負け群の単独差だけでなく、負けに多い特徴の組合せをtraining期間内で抽出し、翌月候補を事前拒否するfamily専用vetoへ変換する。

## 絶対契約

- Stage266Bの時刻・因果・candidate保存契約を継承。
- vetoは当月より前にexit済みの同family tradeだけで作る。
- 当月outcomeを見てruleを変更しない。
- gate featureはpending注文作成時点で既知のものだけ。
- individual trade ID・年・source IDをrule条件へ使わない。
- raw / model accepted / veto rejected / final acceptedを全件保存。

## adverse rule generation

各family・各月のtraining内で実施。

1. Stage266Bの安定feature selection条件を通った上位8featureを候補とする。
2. featureごとに、勝ち平均が負け平均より高ければtraining Q25以下をadverse、低ければQ75以上をadverseとする。
3. single ruleと上位6feature間のpairwise AND ruleを作る。
4. eligible rule条件:
   - training support 10〜35%
   - minimum 8trade
   - training全体cost5 expectancy < 0
   - training loss rateがrawより10 percentage point以上高い
   - training前半・後半の双方でcost5 expectancy < 0
   - training前半・後半の双方でloss rateがraw以上
5. score = loss_capture_rate / candidate_rejection_rate。
6. score順に最大2ruleを選ぶ。
7. 選択ruleのcombined rejectionが35%を超える場合、2本目を使わない。

## final acceptance

- Stage266B family logistic gateでaccepted
- かつ選択adverse ruleに該当しない

の両方を満たす候補だけをfinal acceptedとする。

## 比較出力

familyごとに:

- RAW OOF
- MODEL ONLY
- VETO ONLY
- MODEL + VETO
- VETO REJECTED

についてcount、retention、cost2/cost5 win rate、expectancy、PF、source、direction、top5 profit shareを出す。

## 合格基準

- final accepted 25件以上
- retention 30〜80%
- cost2 win rate >= 60%
- cost5 win rate >= 55%
- cost5 expectancy > 0
- cost5 PF >= 1.25
- veto rejected cost5 expectancy < final accepted
- 2025/2026両source final expectancy >= 0
- LONG/SHORT各10件以上かつfinal expectancy >= 0
- top5 positive profit share <= 60%

基準未達familyはstackへ追加しない。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
