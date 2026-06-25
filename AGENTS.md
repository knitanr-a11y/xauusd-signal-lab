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
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_COST_STRESS_PASS_FRESH_PROSPECTIVE_NEXT_20260625.md`
   - `config/gold_ml_v1/fresh_prospective_confirmation_20260625.json`
   - `config/gold_ml_v1/fresh_prospective_first_run_pass_20260625.json`
   - `config/gold_ml_v1/prospective_monitoring_20260625.json`
   - `config/gold_ml_v1/prospective_monitoring_ci_pass_20260625.json`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_STATEFUL_PROSPECTIVE_MONITOR_CI_PASS_USER_RUN_NEXT_20260625.md`
5. The V2 one-click handoff remains authoritative governance; the latest dated handoff is the operational continuation.
6. Do not ask the user to repeat recorded paths, results or decisions.
7. Periods are frozen: 2023 exploration only; 2024 validation only with no retune; 2025 final test only with no retune; 2026 diagnostic only and never retune.
8. Every exploration must predeclare its search space and record all attempted rules/cells, total search count, failures, survivors and multiplicity. Cherry-picking is forbidden.
9. Silent candidate addition, removal, replacement or relabeling is forbidden.
10. No new exploration may begin before stateful prospective monitoring is initialized and reviewed. Any later exploration requires explicit user authorization and cannot modify the frozen nine.
11. Same-lineage candidates are not independent edges. Do not pool or sum their PF, profit or trades as a portfolio.
12. Batch023 warmup bridge passed 9/9 with zero core mismatch.
13. `RAW_RECONSTRUCTED` and `WARMUP_BRIDGE_EXACT` remain separate. Bridge rows are historical audit only and never live, tuning, exploration, primary cost-stress or promotion rows.
14. This is not raw-only parity because pre-2023 history or serialized seed state remains absent.
15. Replay V1-V5 and ZIP replay are not original generators. Do not rerun them.
16. The only user-facing launcher is repository-root `RUN_GOLD_ML_V1_NEXT.bat`.
17. Phase BATs belong in dedicated subfolders. Current phase BAT: `scripts/gold_ml_v1/monitoring/windows/run_prospective_monitor_cycle.bat`.
18. Users must not run phase BATs directly. The root launcher supplies required arguments.
19. For future phases, commit implementation first, then update `config/gold_ml_v1/next_local_action.json`.
20. Do not give ordinary users Python, PowerShell or long command lines.
21. Private path overrides belong only in gitignored `config/gold_ml_v1/local_runtime_paths.local.json`.
22. Every runner must preserve previous output, validate provenance, write summary/error files, print PASS/FAIL and fail closed on validation errors.
23. The dispatcher writes `outputs/gold_ml_v1/next_action/CURRENT_UPLOAD_PATH.txt`; root BAT opens the phase-selected upload file.
24. Audit-only is mandatory. No live activation, registration, MT5 order, Discord, AI API or live hook.
25. Cost stress is complete: RAW baseline parity 1687, candidate PASS=9 FAIL=0 across all twelve frozen scenarios. Do not rerun it.
26. The first fresh prospective run passed with `NO_CANDIDATE_YET`, zero candidate rows and no error. This is a valid observation and not permission to change rules.
27. Monitoring uses only closed `goldsharp_m1.csv`, `goldsharp_m15.csv`, `goldsharp_h1.csv`, `goldsharp_h4.csv`, `goldsharp_d1.csv` rows strictly after the frozen cutoff.
28. Candidate generation remains causal and cannot use future exit information.
29. Persistent candidate key is `candidate_id + decision_close_time`; persistent parent key is `parent_lineage + decision_close_time`.
30. Existing candidate disappearance, duplicate keys, closed-bar prefix mutation, input truncation, resolved-to-unresolved regression and resolved-result rewrite must fail closed.
31. Allowed candidate transition is only `UNRESOLVED -> RESOLVED`. Unresolved rows remain explicit; synthetic exits/R are forbidden.
32. A parent event may move from frozen non-overlap suppression to accepted only when later bars show the earlier unresolved parent had already exited before that event.
33. Monitoring output updates must be staged and committed transactionally with backups and snapshots.
34. Current monitoring is one cycle per root-BAT execution. No background scheduled task is installed.
35. `NO_NEW_CLOSED_BAR` and `NO_CANDIDATE_YET` are valid PASS observations.
36. Monitoring results cannot retune thresholds, filters, horizons, IDs or lineage membership. There is no prospective performance gate.
37. Before chat length runs out, update AGENTS, current state, next action and a dated handoff.

Current status:

`GOLD_ML_V1_024_STATEFUL_PROSPECTIVE_MONITOR_ONE_CLICK_USER_RUN_READY_AUDIT_ONLY`

Next action:

`USER_PULLS_AND_RUNS_FIRST_STATEFUL_MONITOR_CYCLE_THEN_UPLOADS_PHASE_FILE`
