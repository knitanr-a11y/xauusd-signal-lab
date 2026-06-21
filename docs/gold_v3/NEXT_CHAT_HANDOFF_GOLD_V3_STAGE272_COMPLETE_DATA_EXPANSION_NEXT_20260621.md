# GOLD V3 Stage272 handoff

正式状態: `GOLD_V3_272_R2_BASE_48_72H_ROBUST_NO_EXIT_MANAGEMENT_LEAD_AUDIT_ONLY`

## 完了

- R2 common sample 300
- 22 pre-registered exit/horizon rules
- 2025/2026/latest60/LONG/SHORT/year×direction/path class/monthly/cost2/cost5比較
- current robustness addendum適用
- regression 4/4 PASS

## 結論

- FIXED48とFIXED72は現在もbase horizonとして両方向プラス
- FIXED48 latest60 cost2 expectancy ATR: LONG +1.046 / SHORT +0.956
- FIXED72 latest60: LONG +1.317 / SHORT +0.577
- ただしtail loss/MAEが大きくcomplete strategyではない
- strict exit-management lead 0
- stop/breakevenはcurrent Delayed SHORTを壊す
- structure/trailはFadeを改善するがDelayed/Persistentを削る

## Status

R2: `PATH_EDGE_ONLY_NOT_COMPLETE_STRATEGY`

## Next

- 同じ2025/2026で新exitを追加しない
- 2023-2024 data取得後、固定path-adaptive rulesを外部期間検証
- candidate overlap / one-position suppression / cost executionはその後
- R3はsample監視
- LONG only / SHORT only禁止

運用: `NO_LIVE_PROMOTION_AUDIT_ONLY`
