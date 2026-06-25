# Repository Agent Instructions

## GOLD_ML_V1

1. Use only GOLD_ML_V1. Do not use quarantined legacy GOLD logic or artifacts.
2. Raw CSV `time` is bar-open time in MT5 server time. Latest valid CSV rows are closed.
3. Candidate rules are immutable. Changed logic requires a new candidate ID.
4. New chats must read, in order:
   - `AGENTS.md`
   - `START_HERE_GOLD_ML_V1_NEXT_CHAT.md`
   - `config/gold_ml_v1/current_state_snapshot_20260624.json`
   - `config/gold_ml_v1/next_local_action.json`
   - `config/gold_ml_v1/exploration_guardrails_20260625.json`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXPLORATION_GUARDRAILS_TRIPLE_CHECK_20260625.md`
   - `config/gold_ml_v1/batch023_uploaded_raw_forensic_audit_20260625.json`
   - `config/gold_ml_v1/batch023_warmup_bridge_pass_20260625.json`
   - `config/gold_ml_v1/batch023_local_warmup_bridge_implementation_20260625.json`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_BATCH023_WARMUP_BRIDGE_PASS_20260625.md`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md`
   - `docs/gold_ml_v1/GOLD_ML_V1_EXPLORATION_HANDOFF_FINAL_THREE_PASS_AUDIT_20260625.md`
   - `config/gold_ml_v1/cost_stress_raw_reconstructed_20260625.json`
   - `config/gold_ml_v1/cost_stress_raw_reconstructed_pass_20260625.json`
   - `config/gold_ml_v1/fresh_prospective_confirmation_20260625.json`
   - `config/gold_ml_v1/fresh_prospective_first_run_pass_20260625.json`
   - `config/gold_ml_v1/prospective_monitoring_20260625.json`
   - `config/gold_ml_v1/prospective_monitoring_initialization_pass_20260625.json`
   - `config/gold_ml_v1/exploration_batch024_authorization_20260625.json`
   - `config/gold_ml_v1/exploration_batch024_m15_h1_pullback_20260625.json`
   - `config/gold_ml_v1/exploration_batch024_ci_pass_20260625.json`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ASSISTANT_EXPLORATION_RAW_UPLOAD_NEXT_20260625.md`
5. The V2 one-click handoff remains authoritative governance; the latest dated handoff is the operational continuation.
6. Do not ask the user to repeat recorded paths, results or decisions.
7. Periods are frozen: 2023 exploration only; 2024 validation only with no retune; 2025 final test only with no retune; 2026 diagnostic only and never retune.
8. Every exploration must predeclare its complete search space, gates and execution contract before results; record all attempted cells, failures, survivors, nulls and multiplicity. Cherry-picking is forbidden.
9. Silent candidate addition, removal, replacement or relabeling is forbidden.
10. Batch024 is explicitly user-authorized and is the only currently authorized new exploration scope. It must not modify the frozen nine.
11. The assistant must execute and review Batch024 exploration first. Local execution is not the discovery run.
12. The current user action only packages and transfers the exact-hash frozen M1/M15/H1 RAW inputs. It must not calculate signals, trades, gates or survivors.
13. After the assistant freezes the complete result and hashes, create a local one-click reproducer that compares against the assistant-frozen result and fails closed on any mismatch.
14. Same-lineage candidates are not independent edges. Do not pool or sum their PF, profit or trades as a portfolio.
15. `RAW_RECONSTRUCTED` and `WARMUP_BRIDGE_EXACT` remain separate. Bridge rows are historical audit only and never live, tuning, exploration, primary cost-stress or promotion rows.
16. Replay V1-V5 and ZIP replay are not original generators. Do not rerun them.
17. The only user-facing launcher is repository-root `RUN_GOLD_ML_V1_NEXT.bat`.
18. Current phase BAT: `scripts/gold_ml_v1/exploration/windows/package_batch024_raw_for_assistant.bat`.
19. Users must not run phase BATs directly. The root launcher supplies required arguments and selects the ZIP.
20. Do not give ordinary users Python, PowerShell or long command lines.
21. Private path overrides belong only in gitignored `config/gold_ml_v1/local_runtime_paths.local.json`.
22. Every runner must preserve previous output, validate provenance, write summary/error files, print PASS/FAIL and fail closed on validation errors.
23. Audit-only is mandatory. No live activation, registration, MT5 order, Discord, AI API or live hook.
24. Cost stress is complete: RAW baseline parity 1687, candidate PASS=9 FAIL=0 across all twelve frozen scenarios. Do not rerun it.
25. Stateful monitoring initialization passed locally and its ledger remains preserved. It is not the current root-BAT action.
26. Batch024 uses only exact-hash frozen M1/M15/H1 raw history and never uses `WARMUP_BRIDGE_EXACT`.
27. Batch024 new lineage is `M15_H1_TREND_PULLBACK_LINEAGE_EXP024`, separate from the frozen breakout lineages.
28. Batch024 search space is exactly 36 cells: 2 directions × 3 H1 gap thresholds × 3 M15 RSI levels × 2 trigger modes.
29. Every Batch024 cell has a distinct `GML1-EXP024-*` ID and every cell must remain in the attempt registry regardless of result.
30. Batch024 execution is fixed before results: M15 decision, confirmed H1 context, exact M1 entry, Wilder M15 ATR14 risk, SL 1.0R, TP 1.5R, 720-minute horizon, one position per cell, same-M1 SL priority.
31. 2023 gate is count>=24, PF>=1.10, mean R>0.05. 2024 and 2025 gates are independently count>=18, PF>=1.00, mean R>0. 2026 has no gate and can never retune.
32. Failed cells, suppressed signals, missing exact-M1 entries, unresolved diagnostic rows, nulls and all survivors must be preserved.
33. All-gate-pass Batch024 cells remain `RESEARCH_ONLY`; no automatic accumulation, promotion, registration or modification of the frozen nine.
34. Post-result search-grid, threshold, gate, execution or year-contract changes are forbidden.
35. A zero-survivor Batch024 result is valid and must not trigger rescue tuning.
36. Before chat length runs out, update AGENTS, current state, next action and a dated handoff.

Current status:

`GOLD_ML_V1_026A_RAW_INPUT_TRANSFER_FOR_ASSISTANT_EXPLORATION_READY_AUDIT_ONLY`

Next action:

`USER_UPLOADS_HASH_VERIFIED_RAW_ZIP_THEN_ASSISTANT_EXECUTES_EXPLORATION`
