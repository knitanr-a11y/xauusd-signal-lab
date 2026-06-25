# START HERE - GOLD_ML_V1

Repository: `knitanr-a11y/xauusd-signal-lab`

Current status:

`GOLD_ML_V1_018_COST_STRESS_CORE_REGISTRY_FIX_ONE_CLICK_USER_RERUN_READY_AUDIT_ONLY`

Read `AGENTS.md` first, then follow its mandatory read order exactly.

Mandatory exploration controls:

- `config/gold_ml_v1/exploration_guardrails_20260625.json`
- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXPLORATION_GUARDRAILS_TRIPLE_CHECK_20260625.md`

Authoritative workflow governance handoff:

- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md`

Latest operational continuation handoff:

- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_COST_STRESS_CORE_REGISTRY_FIX_USER_RERUN_NEXT_20260625.md`

The V2 file remains authoritative for governance. The latest dated handoff records the corrected cost-stress schema contract and rerun action.

Important:

- Batch023 warmup bridge has already passed 9/9.
- The first cost-stress attempt failed before producing any candidate result because the loader incorrectly required optional price columns.
- The failed attempt is preserved as `INPUT_SCHEMA_ASSUMPTION_BUG_BEFORE_ANY_COST_STRESS_RESULT`.
- Do not rerun replay V1-V5 or the ZIP replay.
- 2023 is exploration only; 2024 validation only; 2025 final test only; 2026 diagnostic only. No post-result retuning.
- Every exploration cell, failure, survivor and total search multiplicity must be recorded.
- The frozen nine-candidate pool cannot be silently changed or replaced.
- No new exploration begins before cost stress and fresh prospective confirmation unless the user explicitly authorizes a separate audit-only branch.
- The frozen cost grid and gate remain unchanged: spread 1.0x, 1.5x, 2.0x crossed with slippage 0, 5, 10, 20 points per side.
- Cost stress now reads the verified `*_warmup_bridge_core_registry.csv` files.
- `RAW_RECONSTRUCTED` is the only stressed primary population.
- `WARMUP_BRIDGE_EXACT` is reported separately as an exact-core baseline audit and remains `NOT_ELIGIBLE_AUDIT_ONLY`.
- Bridge spread/slippage results must not be invented when pre-2023 state or complete price fields are unavailable.
- The phase BAT is stored in `scripts/gold_ml_v1/cost_stress/windows/`.
- The only user-facing launcher remains the repository-root `RUN_GOLD_ML_V1_NEXT.bat` dispatcher.
- The corrected cost-stress result does not yet exist. The user must rerun the configured one-click action locally.
- After a successful run, stop and review the uploaded summary. Do not automatically begin fresh prospective confirmation.
- Audit-only remains active. No live activation, registration, promotion, Discord, AI API, live hook, final signal, or MT5 order.
