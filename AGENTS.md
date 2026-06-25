# Repository Agent Instructions

## GOLD_ML_V1

1. Use only GOLD_ML_V1. Never read or use quarantined legacy GOLD, GOLD V2, DISC8 or Stage41 assets.
2. Raw CSV `time` is MT5 server bar-open time. Close time is open plus timeframe.
3. Candidate rules are immutable. Changed logic requires a new candidate ID.
4. Read first:
   - `START_HERE_GOLD_ML_V1_NEXT_CHAT.md`
   - `config/gold_ml_v1/current_state_snapshot_20260624.json`
   - `config/gold_ml_v1/next_local_action.json`
   - `config/gold_ml_v1/exploration_batch029_m5_confirmation_result_20260625.json`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_BATCH029_M5_CONFIRMATION_COMPLETE_20260625.md`
5. Periods remain frozen: 2023 exploration; 2024 validation without retune; 2025 final test without retune; 2026 diagnostic only.
6. Predeclare search spaces, gates and execution contracts. Preserve all attempts and failures. Cherry-picking is forbidden.
7. Existing frozen nine remain unchanged.
8. Batch029 completed six event families, three M5 confirmation waits, two execution profiles, composite loss rules and a 2023-trained logistic filter.
9. Batch029 accepted candidates: zero.
10. A post-hoc combined LONG diagnostic is not a clean candidate and failed the frozen cost-stress requirement, passing 6 of 12 scenarios.
11. Rescue tuning, near-miss promotion and post-result filter changes are forbidden.
12. Do not create local exploration, reproduction or implementation until a clean non-duplicate candidate passes 2023, 2024, 2025 and separate cost review.
13. `RUN_GOLD_ML_V1_NEXT.bat` is status-only. No user action is required.
14. Audit-only is mandatory. Live signals, MT5 orders, Discord, AI API, promotion and registration remain off.
15. Before chat length runs out, update AGENTS, current state, next action and a dated handoff.

Current status:

`GOLD_ML_V1_029_M5_CONFIRMATION_RESEARCH_COMPLETE_ZERO_ACCEPTED_CANDIDATES_AUDIT_ONLY`

Next action:

`WAIT_FOR_NEXT_EXPLICIT_RESEARCH_DIRECTION_NO_LOCAL_ACTION`
