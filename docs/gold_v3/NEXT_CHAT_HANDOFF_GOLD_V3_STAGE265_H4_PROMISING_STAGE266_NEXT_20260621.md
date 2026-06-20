# GOLD V3 Stage265 handoff

正式状態: `GOLD_V3_265_H4_INTRABAR_BREAKOUT_PROMISING_NOT_VALIDATED_AUDIT_ONLY`

H1 intrabarはREJECT。H4 intrabarは事前基準11/11 PASS。

固定H4 contract:
- 完了H4+D1だけで方向と6本channel水準を固定
- 次H4 bar内部のM1 gap/touchでpending stop約定
- SL1.25 ATR / TP2.5 ATR / 最大8時間
- UTC20:00を越えない
- same M1はSL優先

結果:
- 67 trades
- cost2 PnL +247.39 / exp +3.692 / PF1.418
- cost5 PnL +46.39 / exp +0.692 / PF1.067
- 2025 52件 exp +3.813
- 2026 15件 exp +3.273
- LONG +124.68 / SHORT +122.71
- candidate prefix 12/12、prefix streaming replay 16/16、tests 4/4 PASS

禁止:
- ATR倍率変更
- channel本数変更
- LONG/SHORT片側化
- time window変更
- 2025/2026で追加最適化

次はStage266 execution-cost/calendar/state-machine hardening。新しいfuture paper holdout前にlive昇格しない。

運用: `NO_LIVE_PROMOTION_AUDIT_ONLY`
