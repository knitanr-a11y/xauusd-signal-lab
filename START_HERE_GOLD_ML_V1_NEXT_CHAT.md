# START HERE — GOLD_ML_V1

Repository: `knitanr-a11y/xauusd-signal-lab`

Current status:

`GOLD_ML_V1_016_BATCH023_WARMUP_BRIDGE_9_OF_9_CORE_PARITY_PASS_ONE_CLICK_WORKFLOW_READY_AUDIT_ONLY`

Read `AGENTS.md` first, then follow its mandatory read order.

Mandatory exploration controls:

- `config/gold_ml_v1/exploration_guardrails_20260625.json`
- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXPLORATION_GUARDRAILS_TRIPLE_CHECK_20260625.md`

Authoritative complete workflow handoff:

- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md`

The V2 file supersedes the earlier one-click handoff.

Important:

- Batch023 warmup bridge has already passed 9/9.
- Do not rerun replay V1-V5 or the ZIP replay.
- 2023 is exploration only; 2024 validation only; 2025 final test only; 2026 diagnostic only. No post-result retuning.
- Every exploration cell, failure, survivor and total search multiplicity must be recorded.
- The frozen nine-candidate pool cannot be silently changed or replaced.
- No new exploration begins before current cost stress and fresh prospective confirmation unless the user explicitly authorizes a separate audit-only branch.
- `WARMUP_BRIDGE_EXACT` is never used for exploration, tuning, cost-stress primary populations, or live decisions.
- The next phase is cost stress on `RAW_RECONSTRUCTED` rows, with `WARMUP_BRIDGE_EXACT` reported separately.
- The only user-facing launcher is `RUN_GOLD_ML_V1_NEXT.bat`.
- A new chat must implement and commit the next phase, update `config/gold_ml_v1/next_local_action.json`, run governance tests, then tell the user only to Pull and double-click the common BAT.
- Audit-only remains active. No live activation or registration.
