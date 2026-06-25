# Repository Agent Instructions

## GOLD_ML_V1

1. Use only GOLD_ML_V1. Never read or use quarantined legacy GOLD, GOLD V2, DISC8 or Stage41 assets.
2. Raw CSV `time` is MT5 server bar-open time. Close time is open plus timeframe.
3. Candidate rules are immutable. Changed logic requires a new candidate ID.
4. Read first:
   - `START_HERE_GOLD_ML_V1_NEXT_CHAT.md`
   - `config/gold_ml_v1/current_state_snapshot_20260624.json`
   - `config/gold_ml_v1/next_local_action.json`
   - `config/gold_ml_v1/exploration_guardrails_20260625.json`
   - `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_BATCH025_028_RESEARCH_RESET_20260625.md`
5. Periods remain frozen: 2023 exploration; 2024 validation with no retune; 2025 final test with no retune; 2026 diagnostic only.
6. Predeclare every search space, gate and execution contract. Record all attempts and failures. Cherry-picking is forbidden.
7. Same-lineage variants are not independent edges. Do not pool their trades or PF as a portfolio.
8. Existing frozen nine remain unchanged.
9. Batch024 through Batch028 produced no accepted survivor.
10. Batch028 was rejected despite being close to the 2024 gate. Near-miss promotion and rescue tuning are forbidden.
11. Stop rescuing Batch024 descendants. Research independent event families instead of threshold clones.
12. Require at least 200 resolved 2023 trades before composite loss analysis.
13. Composite loss exclusions use 2 or 3 decision-time features and at most two sequential rules.
14. Discover loss conditions in 2023 H1 and require the same conditions to work in 2023 H2.
15. Apply frozen conditions unchanged to 2024 and 2025. Use 2026 only for diagnostics.
16. Do not create local exploration, reproduction or implementation until a non-duplicate candidate passes 2023, 2024, 2025 and a separate cost review.
17. `RUN_GOLD_ML_V1_NEXT.bat` is currently status-only. No user action is required.
18. Audit-only is mandatory. Live signals, MT5 orders, Discord, AI API, promotion and registration remain off.
19. Before chat length runs out, update AGENTS, current state, next action and a dated handoff.

Current status:

`GOLD_ML_V1_028_NEW_BASE_FAMILY_RESEARCH_ASSISTANT_SIDE_AUDIT_ONLY`

Next action:

`ASSISTANT_CONTINUES_NEW_BASE_FAMILY_RESEARCH_NO_USER_LOCAL_ACTION`
