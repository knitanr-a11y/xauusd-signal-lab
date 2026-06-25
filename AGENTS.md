# Repository Agent Instructions

## GOLD_ML_V1

1. Use only GOLD_ML_V1. Do not use quarantined legacy GOLD logic or artifacts.
2. Raw CSV `time` is bar-open time in MT5 server time. Latest CSV rows are closed.
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
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_COST_STRESS_IMPLEMENTED_USER_RUN_NEXT_20260625.md`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_COST_STRESS_CORE_REGISTRY_FIX_USER_RERUN_NEXT_20260625.md`
   - `config/gold_ml_v1/cost_stress_raw_reconstructed_pass_20260625.json`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_COST_STRESS_PASS_FRESH_PROSPECTIVE_NEXT_20260625.md`
5. The V2 one-click handoff remains the authoritative governance handoff; the latest dated handoff is the current operational continuation record.
6. Do not ask the user to repeat paths, results, or decisions already recorded there.
7. Exploration periods are frozen: 2023 exploration only; 2024 validation only with no retune; 2025 final test only with no retune; 2026 diagnostic only and never retune.
8. Every exploration must predeclare its search space, record every attempted rule/parameter cell, total search count, failures, survivors, and multiplicity. Cherry-picking only the best PF, win rate, seed, neighborhood cell, or year is forbidden.
9. Candidate-pool silent addition, removal, replacement, or relabeling is forbidden. Every candidate must remain explicitly accumulated, research-only, demoted with reason, or rejected with reason.
10. No new exploration may begin before cost stress and fresh prospective confirmation. A separate branch requires explicit user authorization, remains audit-only, and must not modify the frozen nine.
11. Same-lineage candidates are not independent edges. Do not sum them as a portfolio.
12. Batch023 warmup bridge passes 9/9 candidates with zero missing/extra, entry, exit, R, or direction mismatch.
13. Rows are labeled `RAW_RECONSTRUCTED` or `WARMUP_BRIDGE_EXACT`. Bridge rows are historical audit only and never live signals, exploration rows, tuning rows, primary cost-stress rows, or promotion rows.
14. This is not raw-only parity. Pre-2023 history or serialized indicator state is still absent.
15. Replay V1-V5 and the ZIP replay are not original/exact replay tools. Do not rerun them.
16. The only user-facing launcher is repository-root `RUN_GOLD_ML_V1_NEXT.bat`.
17. Phase BAT files belong in a dedicated phase subfolder. The completed cost-stress BAT is `scripts/gold_ml_v1/cost_stress/windows/run_cost_stress_raw_reconstructed.bat`.
18. For each future phase, first commit the phase implementation, then update `config/gold_ml_v1/next_local_action.json`. Tell the user only to Pull and double-click `RUN_GOLD_ML_V1_NEXT.bat` after the phase is ready.
19. Do not give ordinary phase users Python, PowerShell, or long command lines.
20. Private path overrides belong only in gitignored `config/gold_ml_v1/local_runtime_paths.local.json`.
21. Every runner must create outputs, preserve previous output safely, validate provenance, print PASS/FAIL, return 0 only for validation/report PASS, and write a latest summary and error trace.
22. Audit-only remains mandatory. No live activation, registration, MT5 order, Discord, AI API, or live hook.
23. The cost-stress grid is frozen in `config/gold_ml_v1/cost_stress_raw_reconstructed_20260625.json`: spread 1.0x/1.5x/2.0x crossed with fixed slippage 0/5/10/20 points per side. Do not change it after results.
24. Cost stress completed successfully with RAW baseline parity 1687 and candidate gate PASS=9 FAIL=0. Do not rerun or reinterpret it as live authorization.
25. Cost stress used `RAW_RECONSTRUCTED` as the only stressed primary population and wrote `WARMUP_BRIDGE_EXACT` separately with `NOT_ELIGIBLE_AUDIT_ONLY` gate status.
26. The authoritative cost-stress registry input is each `*_warmup_bridge_core_registry.csv`. Optional exact-schema price columns are not required.
27. `WARMUP_BRIDGE_EXACT` exact spread/slippage replay must not be fabricated when pre-2023 state or complete price/risk fields are absent.
28. A candidate stress-gate FAIL would be a preserved result, not a runner error and not permission to retune. The verified run had zero candidate FAILs.
29. The cost-stress runner stopped after reporting and did not automatically begin fresh prospective confirmation.
30. Fresh prospective confirmation must use closed `goldsharp_m1.csv`, `goldsharp_m15.csv`, `goldsharp_h1.csv`, `goldsharp_h4.csv`, and `goldsharp_d1.csv` bars strictly after `2026-06-23 18:15:00` MT5 server close and requires a separately committed phase.
31. Fresh prospective candidate generation must be causal; unresolved candidates remain explicit; prospective results must not retune thresholds or rules.
32. Before chat length runs out, update AGENTS, current state, next action, exploration guardrails if changed, and a dated handoff.

Current status:

`GOLD_ML_V1_021_COST_STRESS_PASS_FRESH_PROSPECTIVE_IMPLEMENTATION_NEXT_AUDIT_ONLY`

Next action:

`IMPLEMENT_FRESH_PROSPECTIVE_CONFIRMATION_AS_SEPARATE_AUDIT_ONLY_PHASE`
