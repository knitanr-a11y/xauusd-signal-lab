# START HERE - GOLD_ML_V1

Repository: `knitanr-a11y/xauusd-signal-lab`

Current status:

`GOLD_ML_V1_027_BATCH024_ASSISTANT_RESULT_FROZEN_LOCAL_REPRODUCTION_READY_AUDIT_ONLY`

Read `AGENTS.md` first, then follow its mandatory read order exactly.

Mandatory exploration controls:

- `config/gold_ml_v1/exploration_guardrails_20260625.json`
- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXPLORATION_GUARDRAILS_TRIPLE_CHECK_20260625.md`

Authoritative workflow governance:

- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md`

Latest operational continuation:

- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_BATCH024_ZERO_SURVIVORS_LOCAL_REPRODUCTION_NEXT_20260625.md`

Batch024 records:

- `config/gold_ml_v1/exploration_batch024_authorization_20260625.json`
- `config/gold_ml_v1/exploration_batch024_m15_h1_pullback_20260625.json`
- `config/gold_ml_v1/exploration_batch024_ci_pass_20260625.json`
- `config/gold_ml_v1/exploration_batch024_assistant_result_20260625.json`

Assistant-side result:

- `time` is MT5 server bar-open time;
- M1 close = `time + 1 minute`;
- M15 close = `time + 15 minutes`;
- H1 close = `time + 1 hour`;
- attempted cells: 36;
- year metric rows: 144;
- signal/trade audit rows: 25,327;
- survivors: 0;
- two independent assistant replays were equal;
- no rescue tuning or candidate addition was performed.

The existing frozen nine remain unchanged.

Current root action is local reproduction only. It recalculates the frozen grid and compares four canonical output hashes against the assistant result. Any mismatch fails closed.

User action:

1. Pull `main` in GitHub Desktop.
2. Double-click repository-root `RUN_GOLD_ML_V1_NEXT.bat`.
3. Upload the selected file:

`outputs/gold_ml_v1/exploration_batch024_local_reproduction/UPLOAD_THIS_GOLD_ML_V1.txt`

Internal phase BAT:

`scripts/gold_ml_v1/exploration/windows/reproduce_batch024.bat`

Do not run the internal BAT directly. This is not a new exploration or selection run.

Audit-only remains active. All live, order, notification, promotion and registration switches remain off.
