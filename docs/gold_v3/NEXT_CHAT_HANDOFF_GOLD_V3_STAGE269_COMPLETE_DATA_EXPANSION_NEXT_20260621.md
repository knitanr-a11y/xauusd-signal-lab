# GOLD V3 Stage269 handoff

正式状態: `GOLD_V3_269_2026_APPLICABLE_REGIMES_FOUND_NO_STRICT_SHORT_ENTRY_LEAD_AUDIT_ONLY`

## 2026

R1/R2/R3は2026単独でもLONG/SHORT平均・中央値プラス。ただしStage268で2026を使用済みのためcontaminated provisional applicability。

- R1 weak trend low vol 48h: positive53.85%、median+0.291 ATR。2025より弱化。
- R2 UTC08-11 high vol 48h: positive57.94%、median+0.861。72hより方向バランス良好。
- R3 indecision range 8h: positive59.72%、median+0.431。

## M15/M5

strict entry-resolution lead=0。

Near lead:
- R3 × M15 false-break reclaim
- n178、coverage77.06%、positive58.99%
- paired return improvement+0.119 ATR
- MAE improvement+0.231 ATR
- 2026 SHORT mean -0.054のため正式lead不可

M5は明確なentry timing改善なし。

R2 M5 inside-barとR3 M15 compressionはsubset選別として良好だが、同じcandidateの即時entryよりpaired成績が悪化。entry leadではない。

## 次

1. R3 M15 false-break条件を固定。
2. 2023-2024 M15/M5で再検証。
3. 同期間M1取得後exact entry path。
4. R2 M5 inside-barはsetup-quality filterとして別研究。
5. 現2025/2026でtrigger追加・閾値調整禁止。

運用: `NO_LIVE_PROMOTION_AUDIT_ONLY`
