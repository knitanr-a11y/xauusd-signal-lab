# GOLD V3 Stage266H handoff

正式状態:
`GOLD_V3_266H_NO_NEW_QUALIFIED_COMPONENT_F12_RESEARCH_LEAD_ONLY_AUDIT_ONLY`

## 現在の正式component

C1 H4 six-bar channel gateのみ。

- accepted52
- cost2 WR61.54%
- cost5 WR57.69%
- cost5 expectancy+8.225 USD/oz
- cost5 PF2.075

C1は固定。再調整禁止。

## Stage266F–H探索

24のH4/H1構造候補を追加し、件数30以上の8familyへ月次outer OOF＋inner time validationによるLogistic / RandomForest / GradientBoosting比較を実施。

新規qualified componentは0件。

## 第一research lead

F12 H1 false-break reclaim:

- raw OOF39
- gate accepted18
- cost2/cost5 WR66.67%
- cost5 expectancy+7.879
- cost5 PF2.593
- rejected cost5 expectancy-5.479
- C1 overlap16.67%

不合格理由:

- accepted25件未満
- 2025 expectancy -2.693
- 2026 expectancy +16.337
- SHORT4件
- top5 profit share71.97%

stack/liveへ入れずshadow research only。

## その他

- F4 three-bar base: 2026/SHORT/C1重複依存
- F9 mother bar: 6件全勝だがsample不足
- G9 H4 daily-level reclaim: 5件
- G10 H1 daily-level reclaim: 4件
- C4 previous-bar: 非線形gate後も赤字
- H1 compression / EMA reclaim / NR7: 不採用
- C2 nonlinear: WR59.38%、LONG赤字、C1 overlap81.25%
- C3 nonlinear: 9件、C1 overlap88.89%、利益集中

## 因果

Stage266F/H:
- H4 decision=time+4h: 違反0
- H1 decision=time+1h: 違反0
- D1/H4 source_close<=decision: 違反0

## 次に必要なデータ

同一broker/source identity付きで:

1. 2023-01-25〜2024-12-31 M1
   - F12 H1 leadを固定条件で追加検証

2. 2020-01-01〜2024-12-31 M1
   - F4/F9/G9などH4 leadを固定条件で追加検証

3. timezone、official session calendar、source identityを同時保存

追加データ取得後、候補定義・gate・閾値を変更せず再実行する。

## 禁止

- 同じ2025/2026上でさらに手作り候補を増やす
- F12の閾値調整
- F9/G9/G10を少数成績で採用
- LONG/SHORT片側化
- C1再調整

運用状態:
`NO_LIVE_PROMOTION_AUDIT_ONLY`
