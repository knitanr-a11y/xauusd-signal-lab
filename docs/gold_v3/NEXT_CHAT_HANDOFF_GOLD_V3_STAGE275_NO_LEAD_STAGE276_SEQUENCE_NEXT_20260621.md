# GOLD V3 Stage275 handoff

正式状態: `GOLD_V3_275_NO_DISCOVERY_LEAD_LIVE_REPRODUCIBLE_AUDIT_ONLY`

## 完了

- 全M15確定足decision universe
- LONG/SHORT方向展開 161,990 rows
- 96 causal numeric features
- 2023-only 6-regime router
- LR_GLOBAL / HGB_GLOBAL / HGB_ROUTED
- FF1_24H quality model + POS24 direction model
- 81 pre-registered candidate cells
- fixed 1ATR SL / 1.5ATR TP / 24h cap
- 256 prefix feature parity checkpoints
- model score chunk and one-row parity
- 81/81 batch-stream candidate replay parity

## 結論

- live reproducibility: PASS
- discovery leads in 2024: 0/81
- selected cells: 0
- no cell promoted to 2025 or 2026

Best 2024 cell:

`LR_GLOBAL_Q85_M02_C16H`

- n=288
- LONG 250 / SHORT 38
- mean gross +0.189R
- median -1R
- cost2 expectancy -1.345 USD/oz
- PF 0.484

HGB models overfit 2023 strongly:

- HGB_GLOBAL direction AUC 0.878 -> 2024 0.538
- HGB_ROUTED direction AUC 0.962 -> 2024 0.511

Top ten diagnostic cells remain cost-negative in 2025. 2026でほぼzeroとなるLR 4h cellもlatest60はnegative。

## Live contract

- time is bar OPEN time
- M15 decision at +15m close
- H1/H4/D1 only if source_close_time <= decision_time
- next real M1 open entry proxy
- no future fill / interpolation / source fallback
- future path values labels only
- same-M1 SL priority
- batch and streaming identity required

## Next Stage276

`GOLD_V3_276_SEQUENCE_AND_STATE_TRANSITION_DISCOVERY_AUDIT_ONLY`

Stage275のstatic snapshot featureを追加調整しない。

新しい軸:

1. M15 32〜64本の順序sequence
2. volatility compression→expansion transition
3. H1/H4 trend transition
4. regime cluster transition and dwell time
5. session-start path sequence
6. early MFE/MAE path-quality prediction
7. expanding monthly walk-forward model
8. stateful live feature/model hidden-state parity before performance evaluation

研究は停止しない。ただしStage275の81cellをthreshold変更で救済しない。

運用状態: `NO_LIVE_PROMOTION_AUDIT_ONLY`
