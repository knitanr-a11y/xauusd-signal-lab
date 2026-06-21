# GOLD V3 Stage270 handoff

正式状態: `GOLD_V3_270_2025_2026_REGIME_DIFFERENCE_AND_RECENCY_DECAY_COMPLETE_AUDIT_ONLY`

## 2025 vs 2026

Seasonally matched 2025-01-13〜06-19 vs 2026-01-13〜06-19:

- price +25.23% vs -9.32%
- D1 LONG 97.38% / SHORT 0% vs LONG 44.24% / SHORT 45.98%
- H1 ATR/price 0.301% vs 0.469%
- H4 ATR/price 0.616% vs 0.951%
- H4 STRONG_TREND 53.18% vs 41.57%
- H4 WEAK_TREND 9.60% vs 21.30%
- H4 COMPRESSION 9.45% vs 17.60%
- H1/H4/D1 all-aligned 46.66% vs 32.52%

2025は一方向bull trend、2026は高い基礎volatility内でcompression/range/direction reversalが増えた。

## Regime recency

### R1 weak trend × low vol / 48h
- 2025 median +2.983ATR
- 2026 median +0.291ATR
- latest60 overall +2.150ATRだが LONG -4.514 / SHORT +5.370
- latest30 mean -0.434
- status: CURRENTLY_UNSTABLE
- symmetric development停止、research-only

### R2 UTC08-11 × high vol / 48h
- 2025 median +0.746ATR
- 2026 median +0.861ATR
- latest90 LONG/SHORT両方プラス
- latest60 mean +1.086 / median +0.567
- status: CURRENTLY_MAINTAINED with direction divergence warning
- Stage271第一対象

### R3 indecision × range / 8h
- 2025 median +0.155ATR
- 2026 median +0.431ATR
- latest60 LONG mean -0.215 / SHORT +0.810
- status: WEAKENED_BUT_POSITIVE
- Stage271第二対象

## Path timing

- R1: persistent 40.6%→29.8%、fade 7.2%→23.6%
- R2: persistent維持、latest60 delayed 35.3%
- R3: persistent維持だがrecent SHORT偏重

## Next Stage271

`GOLD_V3_271_CURRENT_REGIME_DIRECTION_STABILITY_AUDIT_ONLY`

1. 新entry triggerは増やさない。
2. R2 direction divergenceのentry-known原因を診断。
3. R3 recent LONG failureのentry-known原因を診断。
4. R1はresearch-onlyのまま。
5. M15 false-break near-leadはR3方向安定性解消まで昇格しない。
6. pre-2025 M15/M5/M1取得まではtrigger threshold調整禁止。
7. LONG only / SHORT only禁止。

運用: `NO_LIVE_PROMOTION_AUDIT_ONLY`
