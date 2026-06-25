# START HERE - GOLD_ML_V1

Repository: `knitanr-a11y/xauusd-signal-lab`

Current status:

`GOLD_ML_V1_017_COST_STRESS_IMPLEMENTED_ONE_CLICK_USER_RUN_READY_AUDIT_ONLY`

Read `AGENTS.md` first, then follow its mandatory read order exactly.

Mandatory exploration controls:

- `config/gold_ml_v1/exploration_guardrails_20260625.json`
- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXPLORATION_GUARDRAILS_TRIPLE_CHECK_20260625.md`

Authoritative workflow governance handoff:

- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md`

Latest operational continuation handoff:

- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_COST_STRESS_IMPLEMENTED_USER_RUN_NEXT_20260625.md`

The V2 file remains authoritative for governance. The dated cost-stress file records the current implementation and next local action.

Important:

- Batch023 warmup bridge has already passed 9/9.
- Do not rerun replay V1-V5 or the ZIP replay.
- 2023 is exploration only; 2024 validation only; 2025 final test only; 2026 diagnostic only. No post-result retuning.
- Every exploration cell, failure, survivor and total search multiplicity must be recorded.
- The frozen nine-candidate pool cannot be silently changed or replaced.
- No new exploration begins before cost stress and fresh prospective confirmation unless the user explicitly authorizes a separate audit-only branch.
- `WARMUP_BRIDGE_EXACT` is never used for exploration, tuning, model selection, cost-stress primary populations, promotion, prospective decisions, or live decisions.
- The cost-stress grid was frozen before execution: spread 1.0x, 1.5x, 2.0x crossed with slippage 0, 5, 10, 20 points per side.
- Cost stress uses `RAW_RECONSTRUCTED` as primary and writes bridge results separately.
- The cost-stress result does not yet exist. The user must run the configured one-click action locally.
- The only user-facing launcher is `RUN_GOLD_ML_V1_NEXT.bat`.
- After a successful cost-stress run, stop and review the uploaded summary. Do not automatically begin fresh prospective confirmation.
- Audit-only remains active. No live activation, registration, promotion, Discord, AI API, live hook, final signal, or MT5 order.
