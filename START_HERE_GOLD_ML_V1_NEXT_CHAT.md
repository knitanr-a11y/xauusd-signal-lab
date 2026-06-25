# START HERE - GOLD_ML_V1

Repository: `knitanr-a11y/xauusd-signal-lab`

Current status:

`GOLD_ML_V1_021_COST_STRESS_PASS_FRESH_PROSPECTIVE_IMPLEMENTATION_NEXT_AUDIT_ONLY`

Read `AGENTS.md` first, then follow its mandatory read order exactly.

Mandatory exploration controls:

- `config/gold_ml_v1/exploration_guardrails_20260625.json`
- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXPLORATION_GUARDRAILS_TRIPLE_CHECK_20260625.md`

Authoritative workflow governance handoff:

- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md`

Latest operational continuation handoff:

- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_COST_STRESS_PASS_FRESH_PROSPECTIVE_NEXT_20260625.md`

Verified cost-stress result record:

- `config/gold_ml_v1/cost_stress_raw_reconstructed_pass_20260625.json`

Important:

- Batch023 warmup bridge passed 9/9 with zero core mismatches.
- The corrected cost-stress run completed with exit code 0.
- RAW baseline parity checks: 1687.
- Frozen cost-stress candidate gate: PASS=9, FAIL=0.
- All frozen nine candidates passed all frozen twelve cost scenarios.
- Do not rerun cost stress.
- `RAW_RECONSTRUCTED` remains the only stressed primary population.
- `WARMUP_BRIDGE_EXACT` remains a separate exact-core audit and is not eligible for live use or promotion.
- Candidate rules, IDs, periods, grid and gates remain frozen. No post-result retuning.
- Fresh prospective confirmation is the next phase and must be implemented separately.
- Fresh prospective uses closed goldsharp bars strictly after `2026-06-23 18:15:00` MT5 server close.
- The current root launcher action is status-only; no local rerun is required now.
- Audit-only remains active. All registration, promotion and execution switches remain off.
