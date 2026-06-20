# GOLD V3 Stage266G 定義固定
## Nonlinear loss-gate benchmark for broad candidates

作成日: 2026-06-21  
状態: `GOLD_V3_266G_NONLINEAR_LOSS_GATE_BENCHMARK_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

線形logistic gateで分離できなかった候補について、entry-known特徴の非線形相互作用で負けを事前分離できるかを月次walk-forward OOFで監査する。

## 対象family

- C2_PULLBACK
- C4_PREV_BAR
- C3_COMPRESSION
- F4_THREE_BAR_BASE
- F11_H1_FOUR_BAR_COMPRESSION
- F12_H1_FALSE_BREAK_RECLAIM
- F13_H1_EMA20_RECLAIM
- F14_H1_NR7_RELEASE

raw resolved30件未満familyはモデル監査対象外。

## 絶対契約

- audit-only。
- raw candidate・outcomeは既存固定台帳を使用し、候補定義を変更しない。
- gate featureはpending注文作成時点で既知の情報だけ。
- directionはentry-known categorical featureとして使用可能だが、LONG/SHORT片側除外ruleは禁止。
- source ID、年、月、trade IDをfeatureへ使わない。
- outcome、exit理由、MFE/MAE、fill後情報は禁止。
- 正式評価は月次expanding OOFのみ。
- 各月のモデル種類・retentionは、その月以前のtrainingをさらにold70%/recent30%へ分けたinner time validationだけで選択。

## model candidates

1. Elastic-net LogisticRegression
   - C=0.2、l1_ratio=0.5、class_weight=balanced

2. RandomForestClassifier
   - n_estimators=300
   - max_depth=3
   - min_samples_leaf=10
   - max_features=sqrt
   - class_weight=balanced_subsample
   - random_state=266

3. HistGradientBoostingClassifier
   - max_leaf_nodes=7
   - max_depth=3
   - learning_rate=0.05
   - max_iter=120
   - min_samples_leaf=10
   - l2_regularization=2.0
   - random_state=266

## target

`cost2_pnl > 0`

cost5はstress判定に使用する。

## feature universe

Stage266Fのentry-known featureに加え:

- direction_sign
- entry timeframe indicator
- interactionをtree/boostingが内部学習

source ID・年・月は含めない。

## inner model selection

各外側月のtrainingを時系列でold70% / recent30%に分ける。

各model・retention 40/55/70/85%についてold部分でfitし、recent部分を評価。

eligible:
- validation accepted>=8
- cost2 win rate>=60%
- cost5 expectancy>0

eligibleの中から:
1. cost2 win rate最大
2. cost5 expectancy最大
3. retention最大

eligibleなし:
1. cost2 win rate最大
2. cost5 expectancy最大
3. retention最大

選択したmodelとretentionをfull outer trainingへ再fitし、翌月へ適用する。

## 合格基準

- outer OOF accepted>=25
- retention35〜85%
- cost2勝率>=60%
- raw比+5 percentage point以上
- cost5勝率>=55%
- cost5期待値>0
- cost5 PF>=1.25
- rejected cost5期待値<accepted
- 2025/2026両source expectancy>=0
- LONG/SHORT各10件以上かつexpectancy>=0
- top5利益依存<=60%
- C1 decision-time overlap<=70%

## stack

C1 frozenと合格familyだけをone-pending/one-activeで再生し、stack後の実現勝率と月間中央値を評価する。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
