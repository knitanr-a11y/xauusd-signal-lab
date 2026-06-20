# Stage266G Execution Feasibility Addendum

作成日: 2026-06-21

Stage266Gのfamily別正式結果が1件も完成する前に固定する実行仕様修正。

## 修正理由

月次outer OOF内で、3modelをinner time validationし、RandomForest 300本を全familyで再学習する構成は計算上限内で完了しなかった。候補定義・feature・target・評価基準は変更しない。

## 修正

- RandomForest n_estimators: 300 -> 100
- HistGradientBoosting max_iter: 120 -> 80
- outer monthly minimum training: 30 resolved trades
- old70% / recent30%、retention候補、model selection、qualification基準は変更なし

## 状態

`GOLD_V3_266G_EXECUTION_FEASIBILITY_ADDENDUM_LOCKED_AUDIT_ONLY`
