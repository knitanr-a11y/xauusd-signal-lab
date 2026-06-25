# Repository Agent Instructions

## GOLD_ML_V1

1. Use only GOLD_ML_V1. Never read or use quarantined legacy GOLD, GOLD V2, DISC8 or Stage41 assets.
2. Raw CSV `time` is MT5 server bar-open time. Close time is open plus timeframe.
3. Candidate rules are immutable. Changed logic requires a new candidate ID.
4. Read first:
   - `START_HERE_GOLD_ML_V1_NEXT_CHAT.md`
   - `config/gold_ml_v1/current_state_snapshot_20260624.json`
   - `config/gold_ml_v1/next_local_action.json`
   - `config/gold_ml_v1/provisional_candidate_gml1_prov_030_a_20260625.json`
   - `config/gold_ml_v1/provisional_candidate_gml1_prov_030_a_pre_admission_audit_20260625.json`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_PROV030A_LOCAL_AUDIT_REPRODUCTION_NEXT_20260625.md`
5. Periods remain frozen: 2023 exploration; 2024 validation without retune; 2025 final test without retune; 2026 diagnostic only.
6. Predeclare search spaces, gates and execution contracts. Preserve all attempts and failures. Cherry-picking is forbidden.
7. Existing frozen accumulated candidates remain nine and are unchanged.
8. `GML1-PROV-030-A` is a separate provisional research-only candidate, not accumulated or registered.
9. The final rule must be applied before M5 confirmation and one-open-position admission. Canonical output is 247 trades with SHA-256 `47912c3131f6917ecae31c13a797568aacca1a08a8b655721d5527e295e579c3`.
10. PROV-030-A passed 12 of 12 cost scenarios and 16 of 25 nearby threshold cells passed both 2024 and 2025 gates.
11. Caveats remain: small 2023 H1 selected leaf, multiplicity-adjusted significance not established, negative quarters, and near-flat 2026 diagnostic.
12. Local audit reproduction is required before prospective monitoring. Any row or hash mismatch must fail closed.
13. The only user-facing launcher is repository-root `RUN_GOLD_ML_V1_NEXT.bat`; do not ask the user to run Python or an internal BAT.
14. No accumulation, registration, live signal, MT5 order, Discord, AI API or automatic promotion is authorized.
15. Before chat length runs out, update AGENTS, current state, next action and a dated handoff.

Current status:

`GOLD_ML_V1_030_PROV030A_PROVISIONAL_COST_PASS_LOCAL_REPRODUCTION_READY_AUDIT_ONLY`

Next action:

`USER_RUNS_PROV030A_LOCAL_AUDIT_REPRODUCTION_AND_UPLOADS_RESULT`
