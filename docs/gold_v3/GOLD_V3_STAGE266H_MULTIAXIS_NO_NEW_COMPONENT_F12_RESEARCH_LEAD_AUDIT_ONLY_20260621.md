# GOLD V3 Stage266F–H 多角的候補探索監査

作成日: 2026-06-21

正式状態: `GOLD_V3_266H_NO_NEW_QUALIFIED_COMPONENT_F12_RESEARCH_LEAD_ONLY_AUDIT_ONLY`

## 結論

C1以外を探すため、H4/H1の継続、押し戻り回復、false-break reclaim、圧縮、mother bar、NR7、EMA squeeze、RSI reset、日足水準reclaim、breakout-retest、初期trend、exhaustion reversalを含む24構造候補を探索した。

さらに、件数30以上の8familyへ、月次outer OOFの内側でLogistic / RandomForest / GradientBoostingを時系列選択する非線形loss gateを適用した。

結果:

- 新規qualification通過family: 0
- C1 frozen componentは引き続き唯一の合格component
- F12 H1 false-break reclaimだけが次研究へ残す価値のあるlead
- 少数だけ良いmother-bar / daily-level / three-bar-baseはsample不足か2026/SHORT集中
- 高頻度C4 previous-bar、H1 compression、EMA reclaim、NR7は非線形gateでも救済不能

## 探索範囲

### Stage266F

H4:
- false-break reclaim
- shallow EMA20 reclaim
- deep pullback recovery
- three-bar base
- NR7 release
- outside continuation
- EMA squeeze release
- RSI reset resume
- mother-bar breakout
- exhaustion rejection reversal

H1:
- four-bar compression
- false-break reclaim
- EMA20 reclaim
- NR7 release

### Stage266H

- H1 sweep strong-close
- H1 sweep low-vol
- H1 mother bar
- H1 engulfing continuation
- H1 three-bar base
- H1 daily-level reclaim
- H4 breakout-retest
- H4 first pullback after EMA cross
- H4 mother bar wide
- H4 daily-level reclaim

## 最重要lead: F12 H1 false-break reclaim

非線形family gate OOF:

- raw OOF: 39件、cost2勝率51.28%
- gate accepted: 18件、retention46.15%
- cost2勝率66.67%
- cost5勝率66.67%
- cost5期待値 +7.879 USD/oz
- cost5 PF 2.593
- rejected cost5期待値 -5.479
- C1 decision-time overlap 16.67%

良い点:

- C1との重複が低い
- acceptedとrejectedの損益差が大きい
- 線形だけでなくRF/GradientBoostingが月によって選ばれ、非線形相互作用が有効

不合格理由:

- accepted18件で最低25件未満
- 2025 accepted期待値 -2.693
- 2026 accepted期待値 +16.337
- SHORTは4件だけ
- top5 positive profit share 71.97%

したがって、componentではなく`RESEARCH_LEAD_ONLY`。

## F4 three-bar base

raw:

- 38件
- cost2勝率55.26%
- cost5勝率52.63%
- cost5期待値 +3.809
- cost5 PF1.566

しかし:

- 2025期待値 -0.491
- 2026期待値 +22.853
- SHORTは5件
- OOF scoredは7件だけ
- scored C1 overlap100%
- top5 share95.04%

最近相場・少数SHORT・C1重複依存のため不採用。

## 少数良好候補

- F9 H4 mother-bar: 6件、6勝
- G9 H4 daily-level reclaim: 5件、cost5期待値+7.578
- G10 H1 daily-level reclaim: 4件、cost5期待値+7.662
- G8 H4 mother-bar wide: 3件、cost5期待値+5.863

これらは興味深いが、統計評価不能。勝率100%などを根拠に採用しない。

## 高頻度候補の結果

### C4 previous-bar breakout

非線形OOF:

- raw188件、勝率52.66%
- accepted117件、勝率51.28%
- cost5期待値 -0.312
- LONG accepted期待値 -3.823
- SHORT accepted期待値 +15.736

方向片側化は禁止。非線形gateでもLONGの負けを安定分離できず不採用。

### H1 four-bar compression

- accepted26件
- cost2勝率46.15%
- cost5期待値+2.426
- cost5 PF1.230

少数大勝で期待値はプラスだが勝率改善なし。component不採用。

### H1 EMA20 reclaim

- accepted45件
- cost2勝率33.33%
- cost5期待値-4.457
- 2025期待値-11.404

不採用。

### H1 NR7

- accepted37件
- cost2勝率43.24%
- cost5期待値-7.714

不採用。

## C2 / C3

C2 nonlinear:

- accepted32件
- cost2勝率59.38%
- cost5期待値+3.819
- PF1.485
- LONG期待値-1.069
- C1 overlap81.25%

改善したがcomponent条件未達。

C3 nonlinear:

- accepted9件、勝率77.78%、期待値+31.566
- C1 overlap88.89%
- top5 share94.19%
- 2026中心

独立componentにならず、raw監視のまま。

## 第二構造探索

Stage266Hではdaily-level reclaim以外の主要候補は弱かった。

- G1 strong-close sweep: 20件、cost5期待値-2.755
- G2 low-vol sweep: 46件、cost5期待値-4.283
- G3 H1 mother bar: 15件、cost5期待値-7.198
- G4 engulfing: 59件、cost5期待値-3.977
- G5 H1 base: 38件、cost5期待値-5.353
- G6 H4 breakout-retest: 13件、cost5期待値-9.383

F12の良さは、単純にstrong closeやlow-vol条件を固定追加すると消えた。固定hard filterではなく、複数特徴を動的に重み付けするgateが必要。

## 因果監査

Stage266F/Hの候補台帳で:

- H4 decision_time = time + 4時間: 違反0
- H1 decision_time = time + 1時間: 違反0
- D1 source_close_time <= decision_time: 違反0
- H4 source_close_time <= decision_time: 違反0

CSV確定足・time=OPEN・entry-known情報契約は維持。

## 現在の判断

1. C1 frozenを唯一の正式componentとして維持。
2. F12をshadow research candidateとして固定し、live/stackへ入れない。
3. F4/F9/G8/G9/G10は追加sample待ち。
4. C2/C3/C4/H1 compression/EMA/NR7は現在形で打ち切る。
5. 同じ2025/2026でさらに手作り候補を増やすとmultiple-testing過学習が強まるため、一旦停止する。

## 次に必要なもの

新component探索を続けるためには、同一brokerの追加M1履歴が必要。

優先:

- 2023-01-25〜2024-12-31 M1: H1 F12の追加検証
- 2020-01-01〜2024-12-31 M1: H4 F4/F9/daily-level候補の追加検証
- source identity、timezone、session calendarを同時保存

追加データ取得後、候補定義とgateを変更せず再実行する。

運用状態: `NO_LIVE_PROMOTION_AUDIT_ONLY`
