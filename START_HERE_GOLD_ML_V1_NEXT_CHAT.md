# START HERE - GOLD_ML_V1

Repository: `knitanr-a11y/xauusd-signal-lab`

Current status:

`GOLD_ML_V1_025_STATEFUL_PROSPECTIVE_MONITOR_INITIALIZED_OPERATIONAL_AUDIT_ONLY`

Read `AGENTS.md` first, then follow its mandatory read order exactly.

Mandatory exploration controls:

- `config/gold_ml_v1/exploration_guardrails_20260625.json`
- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXPLORATION_GUARDRAILS_TRIPLE_CHECK_20260625.md`

Authoritative workflow governance:

- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md`

Latest operational continuation:

- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_MONITOR_INITIALIZED_CONTINUE_CYCLES_20260625.md`

Verified records:

- `config/gold_ml_v1/cost_stress_raw_reconstructed_pass_20260625.json`
- `config/gold_ml_v1/fresh_prospective_first_run_pass_20260625.json`
- `config/gold_ml_v1/prospective_monitoring_ci_pass_20260625.json`
- `config/gold_ml_v1/prospective_monitoring_initialization_pass_20260625.json`

Completed results:

- Batch023 warmup bridge: PASS 9/9 with zero core mismatch
- cost stress: RAW baseline parity 1687; PASS=9, FAIL=0
- first fresh prospective run: PASS, `NO_CANDIDATE_YET`, candidate rows 0
- stateful monitoring implementation and tests: PASS
- first cumulative monitoring cycle: PASS, `MONITOR_INITIALIZED`, run count 1
- latest closed M1 baseline: `2026-06-25 14:36:00`
- cumulative candidates: 0; parent events: 0; error: none

Current monitoring contract:

- `config/gold_ml_v1/prospective_monitoring_20260625.json`
- fixed cutoff: strictly after `2026-06-23 18:15:00` MT5 server close
- frozen nine candidate IDs and rules
- closed goldsharp M1/M15/H1/H4/D1 files only
- cumulative candidate key: `candidate_id + decision_close_time`
- unresolved candidates may only remain unresolved or become resolved
- resolved result rewrites, candidate disappearance, duplicate keys, source-history mutation and truncation fail closed
- transactional ledger update with backups and per-run snapshots
- no retuning, candidate exploration, notification or order

Continuing operation:

1. Pull `main` in GitHub Desktop before the next cycle.
2. After newer closed bars are available, double-click repository-root `RUN_GOLD_ML_V1_NEXT.bat`.
3. Drag the selected file into ChatGPT:

`outputs/gold_ml_v1/prospective_monitoring/UPLOAD_THIS_GOLD_ML_V1.txt`

The internal phase BAT is:

`scripts/gold_ml_v1/monitoring/windows/run_prospective_monitor_cycle.bat`

Do not run the internal BAT directly. The root launcher supplies its required paths.

This performs one monitoring cycle per root-BAT execution. No background scheduled task is installed.

Audit-only remains active. All exploration, registration, promotion and execution switches remain off.
