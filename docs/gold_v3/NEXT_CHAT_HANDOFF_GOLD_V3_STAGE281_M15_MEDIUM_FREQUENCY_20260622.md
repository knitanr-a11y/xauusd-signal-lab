# NEXT CHAT HANDOFF — GOLD V3 Stage281 done

現在の正式状態:
`GOLD_V3_281_M15_MEDIUM_FREQUENCY_NEAR_MISS_NO_ACTIVE_PROMOTION_AUDIT_ONLY`

最初に読む:
1. `docs/gold_v3/GOLD_V3_STAGE281_M15_MEDIUM_FREQUENCY_DISCOVERY_AUDIT_ONLY_20260622.md`
2. `docs/gold_v3/gold_v3_stage281_final_contract.json`
3. `docs/gold_v3/gold_v3_stage281_medium_frequency_yearly.csv`
4. Stage280 report/contract

維持する候補:
- Tier A: `REV_LONG_Q95_BRK6_E175_SHADOW_RESEARCH`（Stage280、変更なし）
- Tier B near miss:
  `M15_CONT_LONG_Q85_EMA20_E225_AFTER_BASE_LOSS_72H_SHADOW_NEAR_MISS`

Tier B:
- 2024: 39件 PF1.793 +97.37 DD26.99
- 2025: 30件 PF2.198 +120.49 DD33.54
- 2026: 14件 PF1.256 +28.21 DD58.87
- cost1.00 PFも全年度1以上
- 2025統合DD58.46 > 固定許容56.08
- 2026統合DD90.10
- したがってSHADOW_NEAR_MISS_ONLY、ACTIVE禁止

絶対維持:
- GOLD V3 audit-only
- GOLD V2 / 旧GOLD / DISC8 / Stage41を読まない
- resolved-only gate: exit_dt <= current entry_dt
- candidate poolを都合よく除外しない
- Router V3変更なし
- 459件rollover版SHADOWのまま
- phase2 HV retest SHADOW-only
- live_ready/final_signal/MT5 order/Discord/partial close OFF
- 2026結果でthreshold/方向/exit/DD許容を救済しない

次:
Stage277 external context availabilityを完了し、確認済み外部sourceだけでTier BのDDクラスターを分離する。
