# START HERE - GOLD_ML_V1

Repository: `knitanr-a11y/xauusd-signal-lab`

Current status:

`GOLD_ML_V1_026A_RAW_INPUT_TRANSFER_FOR_ASSISTANT_EXPLORATION_READY_AUDIT_ONLY`

Read `AGENTS.md` first, then follow its mandatory read order exactly.

Mandatory exploration controls:

- `config/gold_ml_v1/exploration_guardrails_20260625.json`
- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXPLORATION_GUARDRAILS_TRIPLE_CHECK_20260625.md`

Authoritative workflow governance:

- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md`

Latest operational continuation:

- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ASSISTANT_EXPLORATION_RAW_UPLOAD_NEXT_20260625.md`

Verified prerequisite records:

- `config/gold_ml_v1/cost_stress_raw_reconstructed_pass_20260625.json`
- `config/gold_ml_v1/fresh_prospective_first_run_pass_20260625.json`
- `config/gold_ml_v1/prospective_monitoring_initialization_pass_20260625.json`

Batch024 records:

- `config/gold_ml_v1/exploration_batch024_authorization_20260625.json`
- `config/gold_ml_v1/exploration_batch024_m15_h1_pullback_20260625.json`
- `config/gold_ml_v1/exploration_batch024_ci_pass_20260625.json`

Correct execution order:

1. The user transfers the hash-verified frozen RAW archive only.
2. ChatGPT executes and reviews the exploration.
3. ChatGPT freezes complete results and hashes.
4. A local one-click reproducer is created afterward.
5. Local reproduction must match the assistant-frozen result or fail closed.

The current root action does **not** run exploration. It only packages:

- `gold_v3_2023_2026_m1.csv`
- `gold_v3_2023_2026_m15.csv`
- `gold_v3_2023_2026_h1.csv`

Current exploration contract:

- new lineage: `M15_H1_TREND_PULLBACK_LINEAGE_EXP024`
- existing frozen nine remain unchanged
- 36 predeclared cells, all reported
- 2023 exploration only
- 2024 validation only with no retune
- 2025 final test only with no retune
- 2026 diagnostic only and never retune
- all-gate-pass cells remain `RESEARCH_ONLY`
- zero survivors is valid and cannot trigger rescue tuning
- no bridge rows, lookahead, best-cell-only reporting or same-lineage metric pooling
- no automatic accumulation or promotion

User action:

1. Pull `main` in GitHub Desktop.
2. Double-click repository-root `RUN_GOLD_ML_V1_NEXT.bat`.
3. Upload the selected ZIP:

`outputs/gold_ml_v1/exploration_batch024_data_upload/GOLD_ML_V1_BATCH024_FROZEN_RAW_INPUT.zip`

The internal packaging BAT is:

`scripts/gold_ml_v1/exploration/windows/package_batch024_raw_for_assistant.bat`

Do not run the internal BAT directly. No local exploration is authorized yet.

The existing stateful monitoring ledger remains preserved but is not the current root-BAT action.

Audit-only remains active. All live, order, notification, promotion and registration switches remain off.
