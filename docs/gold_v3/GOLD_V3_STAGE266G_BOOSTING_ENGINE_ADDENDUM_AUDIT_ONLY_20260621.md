# Stage266G Boosting Engine Addendum

作成日: 2026-06-21

family別正式結果が完成する前の実行互換修正。

## 理由

HistGradientBoostingClassifierが当該実行環境の小標本/OpenMP構成でfit停止した。候補、feature、target、inner/outer時系列評価、他modelは変更しない。

## 置換

HistGradientBoostingClassifierをGradientBoostingClassifierへ置換する。

- n_estimators=100
- learning_rate=0.05
- max_depth=2
- min_samples_leaf=10
- subsample=0.8
- random_state=266

線形・RandomForestとの3model比較は維持する。

状態: `GOLD_V3_266G_BOOSTING_ENGINE_ADDENDUM_LOCKED_AUDIT_ONLY`
