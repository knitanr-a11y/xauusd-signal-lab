# Repository Agent Instructions

## GOLD_ML_V1

Read first:

1. `START_HERE_GOLD_ML_V1_NEXT_CHAT.md`
2. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GML1_LIVE_AUDIT_AND_NEW_CANDIDATE_DISCOVERY_20260628.md`
3. `config/gold_ml_v1/current_state_20260628.json`
4. `config/gold_ml_v1/next_action_20260628.json`
5. `config/gold_ml_v1/live_research_challenger/live_runtime_contract_20260628.json`
6. `config/gold_ml_v1/research_challenger/runtime_20260628/runtime_contract.json`
7. `docs/gold_ml_v1/CURRENT_GML1_HANDOFF_20260627.md`
8. `config/gold_ml_v1/mlr1_candidate_ml_eligibility_20260627.json`

The 2026-06-28 GitHub handoff is authoritative. Do not ask the user to download or paste another handoff.

Older Stage031/current-state documents remain audit history only and must not be used to restart from the 2026-06-26 status.

### Current formal status

`GML1_LIVE_AUDIT_4_SLEEVES_READY_P16_P19_HISTORICAL_ONLY_NEW_DISCOVERY_NEXT`

### 2026-06-29 user-authorized execution branch override

On branch `gml1-live-discord-mt5-execution-v1-20260629`, the user explicitly authorized continuation of the existing four-sleeve runtime into Discord delivery and MT5 automatic execution.

Read additionally:

1. `docs/gold_ml_v1/GML1_LIVE_DISCORD_MT5_EXECUTION_V1_20260629.md`
2. `config/gold_ml_v1/live_research_challenger/live_execution_contract_20260629.json`

This branch-specific instruction supersedes the general Discord/MT5 prohibition below only for the dedicated delivery/execution adapter. It does not authorize changing the four candidate formulas, enabling P16/P19, retuning historical rules, merging the draft before user-PC verification, or claiming production readiness.

Repository defaults must remain fail-closed: real orders are off unless the Files-root `.env` contains every explicit arming control. The first adapter run is no-backfill. User-PC Discord, dry-run and market-open execution validation are still required.

### Required distinctions

Do not mix:

- the historical accumulated candidate stack;
- the six-sleeve historical research-challenger portfolio;
- the four-sleeve live audit runtime.

The four live-capable sleeves are:

- `A_CORE / GML1-WATCH-022-C`
- `B_STATE / GML1-H1D1-STATEFUL-REENTRY24-C`
- `P18 / GML1-PROV-018-APPROX`
- `W024A / GML1-WATCH-024-A`

P16 and P19 remain historical-only. Their trained models, scalers, feature order, score registries, numeric thresholds and original training/inference code were not recovered. Frozen exclusion decision times are historical-reconstruction truth only and are forbidden for future inference. Do not substitute ML-04 or another model.

ML-05A density v2 was already completed in PR #41. Do not repeat it.

The next authorized research stage is:

`GML1_NEW_INDEPENDENT_CANDIDATE_DISCOVERY_V1_AUDIT_ONLY`

Freeze definitions and label-free density before inspecting labels, WR, PF, R or outcomes.

### Live runtime state

- Persistent BAT loop exists.
- Polling is wall-clock anchored every 2 seconds by default.
- Heavy processing runs only after CSV file change.
- Exact M1 decision-entry row is required.
- Delayed M15/H1/H4/D1 writes are synchronized fail-closed.
- Candidate formulas were not simplified.
- User-PC market-open observation after PR #65/#66 is still unverified.

### Absolute exclusions

- GOLD_ML_V1 only.
- Do not read or use GOLD V2, old GOLD, DISC8 or Stage41.
- Batch024 is closed; do not run, recreate, repair, reorganize, refactor or restart it.
- `GML1-PROV-030-A` is rejected; do not run, recreate, repair, rescue, re-evaluate or use it as fallback.
- Do not use P16/P19 frozen exclusions for new bars.
- Do not retune after inspecting 2025 or 2026.
- Do not modify the live runtime during discovery except to fix a demonstrated defect.
- Unless a later explicit user instruction authorizes a dedicated branch, no final signal, Discord, MT5 order, automatic retraining, promotion or registration.

CSV `time` is MT5 server naive bar-open time. The latest valid CSV row is closed by contract. Do not convert decision logic to JST. Same-M1 target/protective collision resolves protective first. No next-M1 fallback.
