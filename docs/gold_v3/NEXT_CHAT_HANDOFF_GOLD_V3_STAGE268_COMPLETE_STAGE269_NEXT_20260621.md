# GOLD V3 Stage268 handoff

正式状態: `GOLD_V3_268_FORWARD_DISTRIBUTION_AND_REGIME_DIAGNOSTIC_COMPLETE_AUDIT_ONLY`

## 完了

- H1 8,636 / H4 2,257 decisionをATR正規化
- 4/8/12/24/48/72/120取引時間分布を診断
- time、trend/range、volatility、extension、expansion、candle、D1/H4/H1整合、activationを集計
- direction safeguardを追加
- base researchable 573
- direction-biased 415
- strict LONG/SHORT×2025/2026 stable 12 cells / 11 configurations
- acceptance ALL PASS

## 重要結果

- BAR_CONTINUATION単独: edgeなし
- TIMEFRAME_TREND単独: SHORTが2025負/2026正
- D1_TREND: multi-dayで強いが2025 D1 SHORT=0のため未検証方向あり
- MEAN_REVERSION全体: 負
- strict single-axis cell: 0
- strict cellsは全て2条件interaction

## 残す研究family

1. H1 WEAK_TREND × LOW volatility / TIMEFRAME_TREND / 48h
2. H1 LOW volatility × hour-bin / TIMEFRAME_TREND / 24〜72h
3. H1 UTC08-11 × HIGH volatility / BAR_CONTINUATION / 48〜72h
4. H4 candle-state × trend-state BAR_CONTINUATION / 8〜48h

## 次 Stage269

`GOLD_V3_269_PRE2025_COARSE_PATH_VALIDATION_AUDIT_ONLY`

- 11 strict configurationsを固定
- H1 2023-2024、H4 2020-2024でcoarse path validation
- 条件・horizon変更禁止
- exact execution/PnLとは呼ばない
- 年別・方向別符号を確認

## 禁止

- D1_TRENDの見かけの573/445 cellsをそのままstrategy化
- LONG only / SHORT only
- 8時間共通exit
- strict cellの閾値調整
- 旧C1/F12復活

運用: `NO_LIVE_PROMOTION_AUDIT_ONLY`
