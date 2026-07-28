# NEXT CHAT HANDOFF — GOLD V3 Stage282 done

正式状態:
`GOLD_V3_282_DD_CAUSE_CONFIRMED_RISK_NORMALIZATION_SHADOW_ONLY_AUDIT_ONLY`

最初に読む:
1. `docs/gold_v3/GOLD_V3_STAGE282_DD_CAUSE_RISK_NORMALIZATION_AUDIT_ONLY_20260622.md`
2. `docs/gold_v3/gold_v3_stage282_final_contract.json`
3. `docs/gold_v3/gold_v3_stage282_risk_by_year.csv`
4. `docs/gold_v3/gold_v3_stage282_risk_cap_yearly.csv`

重要:
- Stage281 2026 DD58.87は2回のフルSLが中心。
- H1 ATR絶対値上昇でフルSL中央値が7.49(2024)→23.88(2026)へ拡大。
- R-DDは5.63R / 5.79R / 2.04Rで、2026が最小。
- 3月clusterは同一基準損失後の5件集中。
- H4/D1不一致、異常spread、severe M1 shockは主因ではない。
- 2024 median由来7.5 USD full-SL cap診断ではStage281統合DD:
  2024=34.37, 2025=50.42, 2026=52.48。
- ただしpost-DD diagnosticでありSHADOW_DIAGNOSTIC_ONLY。
- true MT5 symbol contractとlot step未確認。

絶対維持:
- GOLD V3 audit-only
- GOLD V2 / 旧GOLD / DISC8 / Stage41を読まない
- Router V3変更なし
- 459件版SHADOWのまま
- Stage280/281候補変更なし
- candidate pool削除なし
- live_ready/final_signal/MT5 order/Discord/partial close OFF

次:
GOLD# symbol contract、volume min/step、tick size/valueをMT5で確認し、
固定口座リスクからlotを計算するaudit-only契約を作る。
