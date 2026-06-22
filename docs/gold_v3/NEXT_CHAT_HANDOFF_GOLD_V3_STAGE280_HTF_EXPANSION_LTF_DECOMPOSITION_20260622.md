# NEXT CHAT HANDOFF — GOLD V3 Stage280 done

現在の正式状態:
`GOLD_V3_280_HTF_EXPANSION_PRECURSOR_FOUND_SHADOW_ONLY_NO_ACTIVE_PROMOTION_AUDIT_ONLY`

最初に読む:
1. `docs/gold_v3/GOLD_V3_STAGE280_HTF_EXPANSION_LTF_DECOMPOSITION_AUDIT_ONLY_20260622.md`
2. `docs/gold_v3/gold_v3_stage280_final_contract.json`
3. 必要なら `docs/gold_v3/gold_v3_stage280_calibrated_model_metrics.csv`
4. 必要なら `docs/gold_v3/gold_v3_stage280_shadow_candidate_yearly.csv`

重要結果:
- H1伸長開始 1,561件をCONT/REV/NEUTRALへ分離。
- REVモデルの校正q95 lift: 2024=2.55, 2025=2.67, 2026=3.09。
- CONTは2026で崩れたため混ぜない。
- 伸長前は新方向と反対へM5 12本で約1～1.5ATR進み、EMA20反対側にいる傾向。
- H1始値entryは早すぎる。M5 Trigger待ちが必要。
- 最有力は `REV_LONG_Q95_BRK6_E175_SHADOW_RESEARCH`。
- 2024/2025/2026候補PF=5.629/1.660/5.009。
- ただし件数12/17/11、利益集中、2026統合DD76.20のためACTIVE化禁止。

絶対維持:
- GOLD V3 audit-only。
- GOLD V2 / 旧GOLD / DISC8 / Stage41を読まない・使わない。
- 現行Specialist Health Router V3を変更しない。
- 459件rollover版はSHADOWのまま。
- phase2 HV retestはSHADOW-only。
- live_ready/final_signal/MT5 order/Discord/partial close OFF。
- feature/gateはentry時点で知り得るclosed情報だけ。
- health/rollingはexit_dt <= current entry_dtのresolved-only。
- 2026を見てthreshold、方向、exitを救済しない。

次:
- Stage277 external context availabilityを完了。
- 確認済み外部sourceだけでREV false-positive分離を行う。
