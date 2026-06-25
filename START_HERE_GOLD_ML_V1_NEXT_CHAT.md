# START HERE - GOLD_ML_V1

Repository: `knitanr-a11y/xauusd-signal-lab`

Current status:

`GOLD_ML_V1_019_COST_STRESS_PASTE_ME_DIAGNOSTIC_USER_RERUN_READY_AUDIT_ONLY`

Read `AGENTS.md` first, then follow its mandatory read order exactly.

Mandatory exploration controls:

- `config/gold_ml_v1/exploration_guardrails_20260625.json`
- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXPLORATION_GUARDRAILS_TRIPLE_CHECK_20260625.md`

Authoritative workflow governance handoff:

- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md`

Latest operational continuation handoff:

- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_COST_STRESS_PASTE_ME_DIAGNOSTIC_USER_RERUN_NEXT_20260625.md`

The V2 file remains authoritative for governance. The latest dated handoff records the diagnostic rerun behavior.

Important:

- Batch023 warmup bridge has already passed 9/9.
- The first cost-stress attempt failed before producing any candidate result because the loader incorrectly required optional price columns.
- The core-registry correction remains in place; the frozen candidate pool, cost grid and gates are unchanged.
- Do not rerun replay V1-V5 or the ZIP replay.
- 2023 is exploration only; 2024 validation only; 2025 final test only; 2026 diagnostic only. No post-result retuning.
- No new exploration begins before cost stress and fresh prospective confirmation unless the user explicitly authorizes a separate audit-only branch.
- `RAW_RECONSTRUCTED` is the only stressed primary population.
- `WARMUP_BRIDGE_EXACT` remains a separate exact-core audit and is not eligible for promotion or live use.
- The phase BAT is stored in `scripts/gold_ml_v1/cost_stress/windows/`.
- The only user-facing launcher remains repository-root `RUN_GOLD_ML_V1_NEXT.bat`.
- The launcher now captures console output, keeps the window open and opens `PASTE_ME_GOLD_ML_V1.txt` in Notepad after PASS or FAIL.
- Paste the complete Notepad contents into ChatGPT; separate log hunting is no longer required.
- The corrected cost-stress result does not yet exist.
- Do not automatically begin fresh prospective confirmation after this run.
- Audit-only remains active. All registration, promotion and execution switches remain off.
