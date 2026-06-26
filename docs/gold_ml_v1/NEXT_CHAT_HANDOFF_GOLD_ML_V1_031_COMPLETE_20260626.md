# GOLD_ML_V1 Stage031 complete handoff

Date: 2026-06-26

Formal status:

`GOLD_ML_V1_031_HANDOFF_READY_AUDIT_ONLY`

Repository:

`knitanr-a11y/xauusd-signal-lab`

## Mandatory read order

1. `AGENTS.md`
2. `START_HERE_GOLD_ML_V1_NEXT_CHAT.md`
3. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_031_COMPLETE_20260626.md`
4. `config/gold_ml_v1/current_state_20260626.json`
5. `config/gold_ml_v1/local_execution_status_20260626.json`
6. `config/gold_ml_v1/next_local_action.json`
7. `config/gold_ml_v1/provisional_candidate_stack_20260624.json`
8. `config/gold_ml_v1/prov030a_rejection_20260626.json`

Do not ask the user to download or paste a separate handoff file. This GitHub document is the handoff.

## Current decision

- Existing accumulated candidate pool: 9.
- Existing nine modified: no.
- Active new candidate: 0.
- `GML1-PROV-030-A`: rejected and inactive.
- Root `RUN_GOLD_ML_V1_NEXT.bat`: status-only.
- Current local action: none.
- New exploration, local reproduction, implementation and monitoring: not authorized.

## Exact local execution progress

### Completed on the user PC and verified from uploaded output

#### RAW reconstructed cost stress

Record: `config/gold_ml_v1/cost_stress_raw_reconstructed_pass_20260625.json`

- Local generation time: 2026-06-25 19:31:38.
- Exit code: 0.
- Baseline parity checks: 1,687.
- Frozen candidates: PASS 9, FAIL 0.
- All nine passed all 12 frozen spread and slippage scenarios.
- Candidate pool was not changed.
- No retuning, promotion, registration or live authorization occurred.

#### Fresh prospective first run

Record: `config/gold_ml_v1/fresh_prospective_first_run_pass_20260625.json`

- Local generation time: 2026-06-25 20:12:06.
- Exit code: 0.
- Observation: `NO_CANDIDATE_YET`.
- Candidate rows: 0.
- Resolved rows: 0.
- Unresolved rows: 0.
- Accepted parent events: 0.
- Error: none.

#### Stateful prospective monitor initialization

Record: `config/gold_ml_v1/prospective_monitoring_initialization_pass_20260625.json`

- Local generation time: 2026-06-25 20:36:30.
- Exit code: 0.
- State: `MONITOR_INITIALIZED`.
- Run count: 1.
- Cutoff MT5 server close: 2026-06-23 18:15:00.
- Latest M1 close: 2026-06-25 14:36:00.
- Candidates: 0.
- Parent events: 0.
- Background task or Windows Scheduled Task: not installed.
- No later monitor cycle is recorded.
- This monitor is historical state only and is not the current root-BAT action.

### Local implementation and verification record

#### Batch023 warmup bridge

Records:

- `config/gold_ml_v1/batch023_local_warmup_bridge_implementation_20260625.json`
- `config/gold_ml_v1/batch023_warmup_bridge_pass_20260625.json`

- RAW hashes: 6 of 6 PASS.
- Candidate parity: 9 of 9 PASS.
- Missing or extra rows: 0.
- Entry mismatches: 0.
- Exit mismatches: 0.
- R-value mismatches: 0.
- Direction mismatches: 0.
- Warmup bridge rows are historical audit rows only.
- Warmup bridge rows are forbidden for live use, promotion, registration or primary cost-stress population use.

## Closed local reproduction work — not pending

The following two items must never be interpreted as unfinished work that should be resumed.

### Batch024 local reproduction

Record: `config/gold_ml_v1/exploration_batch024_local_reproduction_ci_pass_20260625.json`

Historical fact:

- Reproduction code and fail-closed hash checks were implemented.
- GitHub CI tests passed.
- No user-PC parity upload was received.
- Batch024 produced zero survivors.

Current decision:

- Status: `CLOSED_CI_ONLY_DO_NOT_RUN`.
- It is not pending.
- Do not run it on the user PC.
- Do not recreate, repair, reorganize, refactor or reintroduce it as the next action.
- Do not use it to restart Batch024 research.
- Preserve files only as audit history.

### GML1-PROV-030-A local reproduction

Records:

- `config/gold_ml_v1/provisional_candidate_gml1_prov_030_a_ci_pass_20260625.json`
- `config/gold_ml_v1/prov030a_rejection_20260626.json`

Historical fact:

- Reproduction code compiled and passed CI.
- The expected historical registry was 247 rows with a frozen hash.
- It was never run on the user PC.
- It was rejected before a local run.

Current decision:

- Status: `REJECTED_CLOSED_DO_NOT_RUN`.
- It is not pending.
- Do not execute its reproducer.
- Do not recreate, repair, reorganize, refactor, rescue or re-evaluate it.
- Do not use it as a fallback, candidate, monitoring source or starting point.
- Do not add it to the accumulated nine.
- Preserve files only as audit history.
- Restart is forbidden unless the user explicitly reverses the rejection and names this candidate.

## Current candidate pool

1. `GML1-PROV-007`
2. `GML1-PROV-008`
3. `GML1-WATCH-022-B`
4. `GML1-PROV-010`
5. `GML1-PROV-015`
6. `GML1-PROV-020`
7. `GML1-WATCH-021-A`
8. `GML1-WATCH-021-B`
9. `GML1-WATCH-021-C`

Do not silently remove, replace, rename or add candidates. Same-lineage candidates are not independent edges and their PF, profit or trade counts must not be simply pooled.

## Time and data contract

- CSV `time` is MT5 server bar-open time.
- M1 close = time plus 1 minute.
- M5 close = time plus 5 minutes.
- M15 close = time plus 15 minutes.
- H1 close = time plus 1 hour.
- H4 close = time plus 4 hours.
- D1 close = time plus 1 day.
- The latest valid CSV row is closed under the CSV contract.
- Do not treat it as an open or as-of unfinished bar.
- Higher-timeframe joins may use only bars closed by the decision timestamp.
- Future data and lookahead are forbidden.
- Same-M1 TP and SL collision uses SL priority.

## Frozen period contract

- 2023: exploration only.
- 2024: validation only, no retuning.
- 2025: final test only, no retuning.
- 2026: diagnostic only, never retune.

A zero-survivor result is valid. Do not rescue a near miss after viewing 2024, 2025 or 2026.

## Absolute exclusions

- GOLD_ML_V1 only.
- Do not read or use GOLD V2, old GOLD, DISC8, Stage41 or quarantined legacy candidates, models, features or outputs.
- Do not use legacy material as fallback.
- Do not ask the user to repeat stored paths, decisions or results.
- Do not ask the user to run Python, PowerShell or an internal BAT.
- The only user-facing launcher is repository-root `RUN_GOLD_ML_V1_NEXT.bat`.
- No live signal, MT5 order, Discord, AI API, live hook, automatic promotion or automatic registration.
- Do not claim a background process or scheduler exists.
- Do not confuse live-data compatibility with live operation.

## Required first response in the next chat

After reading the mandatory files, state only that:

- Stage031 is handoff-ready.
- The existing nine remain unchanged.
- Active new candidates are zero.
- PROV-030-A is rejected.
- The last user-PC-verified phase is stateful monitor initialization, run count 1, candidates 0.
- Batch024 and PROV-030-A reproduction work is closed, not pending, and must not be run or reorganized.
- Root BAT is status-only.
- The assistant is waiting for explicit user direction.

Do not start exploration, monitoring, local implementation, reproduction or candidate rescue automatically.
