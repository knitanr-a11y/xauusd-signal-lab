# Repository Agent Instructions

## GOLD_ML_V1

1. Use only GOLD_ML_V1. Do not use quarantined legacy GOLD logic or artifacts.
2. Raw CSV `time` is bar-open time in MT5 server time. Latest CSV rows are closed.
3. Candidate rules are immutable. Changed logic requires a new candidate ID.
4. New chats must read, in order:
   - `AGENTS.md`
   - `config/gold_ml_v1/current_state_snapshot_20260624.json`
   - `config/gold_ml_v1/next_local_action.json`
   - `config/gold_ml_v1/batch023_uploaded_raw_forensic_audit_20260625.json`
   - `config/gold_ml_v1/batch023_warmup_bridge_pass_20260625.json`
   - `config/gold_ml_v1/batch023_local_warmup_bridge_implementation_20260625.json`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_BATCH023_WARMUP_BRIDGE_PASS_20260625.md`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_20260625.md`
5. Do not ask the user to repeat paths, results, or decisions already recorded there.
6. Batch023 warmup bridge passes 9/9 candidates with zero missing/extra, entry, exit, R, or direction mismatch.
7. Rows are labeled `RAW_RECONSTRUCTED` or `WARMUP_BRIDGE_EXACT`. Bridge rows are historical audit only and never live signals.
8. This is not raw-only parity. Pre-2023 history or serialized indicator state is still absent.
9. Replay V1-V5 and the ZIP replay are not original/exact replay tools. Do not rerun them.
10. The only user-facing launcher from now on is repository-root `RUN_GOLD_ML_V1_NEXT.bat`.
11. For each future phase, first commit the phase implementation, then update `config/gold_ml_v1/next_local_action.json`. Tell the user only to Pull and double-click `RUN_GOLD_ML_V1_NEXT.bat`.
12. Do not give ordinary phase users Python, PowerShell, or long command lines.
13. Private path overrides belong only in gitignored `config/gold_ml_v1/local_runtime_paths.local.json`.
14. Every runner must create outputs, preserve previous output safely, print PASS/FAIL, return 0 only for PASS, and write a latest summary and error trace.
15. Same-lineage candidates are not independent edges. Do not sum them as a portfolio.
16. 2026 is diagnostic only and cannot be used for retuning.
17. Audit-only remains mandatory. No live activation, registration, MT5 order, Discord, AI API, or live hook.
18. Before chat length runs out, update AGENTS, current state, next action, and a dated handoff.

Current status:

`GOLD_ML_V1_016_BATCH023_WARMUP_BRIDGE_9_OF_9_CORE_PARITY_PASS_ONE_CLICK_WORKFLOW_READY_AUDIT_ONLY`

Next phase:

`IMPLEMENT_COST_STRESS_UPDATE_NEXT_ACTION_THEN_USER_RUNS_RUN_GOLD_ML_V1_NEXT_BAT`
