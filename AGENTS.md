# Repository Agent Instructions

## GOLD_ML_V1

1. Use only GOLD_ML_V1. Do not use quarantined legacy GOLD logic or artifacts.
2. Raw CSV `time` is MT5 server bar-open time. Close time is open plus timeframe.
3. Candidate rules are immutable. Changed logic requires a new candidate ID.
4. New chats must read, in order:
   - `AGENTS.md`
   - `START_HERE_GOLD_ML_V1_NEXT_CHAT.md`
   - `config/gold_ml_v1/current_state_snapshot_20260624.json`
   - `config/gold_ml_v1/next_local_action.json`
   - `config/gold_ml_v1/exploration_guardrails_20260625.json`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXPLORATION_GUARDRAILS_TRIPLE_CHECK_20260625.md`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md`
   - `config/gold_ml_v1/cost_stress_raw_reconstructed_pass_20260625.json`
   - `config/gold_ml_v1/fresh_prospective_first_run_pass_20260625.json`
   - `config/gold_ml_v1/prospective_monitoring_initialization_pass_20260625.json`
   - `config/gold_ml_v1/exploration_batch024_authorization_20260625.json`
   - `config/gold_ml_v1/exploration_batch024_m15_h1_pullback_20260625.json`
   - `config/gold_ml_v1/exploration_batch024_assistant_result_20260625.json`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_BATCH024_ZERO_SURVIVORS_LOCAL_REPRODUCTION_NEXT_20260625.md`
5. The V2 one-click handoff remains authoritative governance; the latest dated handoff is the operational continuation.
6. Do not ask the user to repeat recorded paths, results or decisions.
7. Periods are frozen: 2023 exploration only; 2024 validation only with no retune; 2025 final test only with no retune; 2026 diagnostic only and never retune.
8. Every exploration must predeclare its complete search space, gates and execution contract before results; record all attempts, failures, nulls, survivors and multiplicity. Cherry-picking is forbidden.
9. Silent candidate addition, removal, replacement or relabeling is forbidden.
10. Same-lineage candidates are not independent edges. Do not pool or sum their PF, profit or trades as a portfolio.
11. Batch024 used only exact-hash M1/M15/H1 raw history and never used `WARMUP_BRIDGE_EXACT`.
12. Batch024 `time` semantics are fixed: M1 close=`time+1m`, M15 close=`time+15m`, H1 close=`time+1h`.
13. Batch024 decisions occur at M15 close; entry requires an exact M1 open at that timestamp; H1 joins use only confirmed H1 close times.
14. Batch024 search space is exactly 36 cells: 2 directions × 3 H1 gap thresholds × 3 M15 RSI levels × 2 trigger modes.
15. Batch024 execution is fixed: Wilder M15 ATR14 risk, SL 1.0R, TP 1.5R, horizon 720 minutes, one position per cell, same-M1 SL priority.
16. 2023 gate is count>=24, PF>=1.10, mean R>0.05. 2024 and 2025 gates are independently count>=18, PF>=1.00, mean R>0. 2026 has no gate.
17. Assistant-side Batch024 exploration completed with 36 attempts, 144 year rows, 25,327 signal/trade audit rows and zero survivors.
18. The complete assistant exploration was replayed twice and all four outputs were equal.
19. Zero survivors is a valid result. Rescue tuning, grid expansion, gate changes and post-result filters are forbidden.
20. No Batch024 candidate was added to the frozen nine; no promotion or registration occurred.
21. The only user-facing launcher is repository-root `RUN_GOLD_ML_V1_NEXT.bat`.
22. Current phase BAT: `scripts/gold_ml_v1/exploration/windows/reproduce_batch024.bat`.
23. The current local action is reproduction only. It recalculates the frozen grid and compares canonical hashes against `config/gold_ml_v1/exploration_batch024_assistant_result_20260625.json`.
24. Any local row-count or hash mismatch must fail closed. A mismatched local output is not a valid candidate result.
25. Users must not run phase BATs directly. The root launcher supplies required arguments.
26. Do not give ordinary users Python, PowerShell or long command lines.
27. Private path overrides belong only in gitignored `config/gold_ml_v1/local_runtime_paths.local.json`.
28. Every runner must preserve previous output, validate provenance, write summary/error files, print PASS/FAIL and fail closed on validation errors.
29. Audit-only is mandatory. No live activation, registration, MT5 order, Discord, AI API or live hook.
30. Cost stress is complete: RAW baseline parity 1687, candidate PASS=9 FAIL=0 across all twelve frozen scenarios. Do not rerun it.
31. Stateful monitoring initialization passed and its ledger remains preserved. It is not the current root action.
32. Before chat length runs out, update AGENTS, current state, next action and a dated handoff.

Current status:

`GOLD_ML_V1_027_BATCH024_ASSISTANT_RESULT_FROZEN_LOCAL_REPRODUCTION_READY_AUDIT_ONLY`

Next action:

`USER_RUNS_LOCAL_REPRODUCTION_AND_UPLOADS_PARITY_RESULT`
