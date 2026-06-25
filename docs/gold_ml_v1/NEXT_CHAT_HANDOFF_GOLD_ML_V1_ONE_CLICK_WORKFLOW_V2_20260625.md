# GOLD_ML_V1 — Authoritative One-Click / Exploration Handoff V2

Date: 2026-06-25  
Repository: `knitanr-a11y/xauusd-signal-lab`  
Mode: **AUDIT ONLY**

This V2 file supersedes the earlier one-click handoff. New chats must use this file.

## Mandatory read order

1. `AGENTS.md`
2. `START_HERE_GOLD_ML_V1_NEXT_CHAT.md`
3. `config/gold_ml_v1/current_state_snapshot_20260624.json`
4. `config/gold_ml_v1/next_local_action.json`
5. `config/gold_ml_v1/exploration_guardrails_20260625.json`
6. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXPLORATION_GUARDRAILS_TRIPLE_CHECK_20260625.md`
7. `config/gold_ml_v1/batch023_uploaded_raw_forensic_audit_20260625.json`
8. `config/gold_ml_v1/batch023_warmup_bridge_pass_20260625.json`
9. `config/gold_ml_v1/batch023_local_warmup_bridge_implementation_20260625.json`
10. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_BATCH023_WARMUP_BRIDGE_PASS_20260625.md`
11. This file

Do not ask the user to repeat any path, result, rule, decision, or failure already recorded there.

## Current status

`GOLD_ML_V1_016_BATCH023_WARMUP_BRIDGE_9_OF_9_CORE_PARITY_PASS_ONE_CLICK_WORKFLOW_READY_AUDIT_ONLY`

Verified uploaded local result:

- status PASS
- exit code 0
- six raw hashes match
- nine candidates pass
- missing/extra 0
- entry mismatch 0
- exit mismatch 0
- R mismatch 0
- direction mismatch 0

## Frozen candidate pool

Accumulated audit-only:

- GML1-PROV-007
- GML1-PROV-008
- GML1-WATCH-022-B
- GML1-PROV-010
- GML1-PROV-015
- GML1-PROV-020
- GML1-WATCH-021-A
- GML1-WATCH-021-B
- GML1-WATCH-021-C

Research-only and preserved:

- GML1-WATCH-014-A
- GML1-WATCH-022-A
- GML1-WATCH-023-A

Silent addition, removal, relabeling, or replacement is forbidden.

## Exploration gate

New exploration is currently forbidden.

It remains locked until all of the following are complete:

1. cost stress on `RAW_RECONSTRUCTED` rows;
2. separate reporting of `WARMUP_BRIDGE_EXACT` rows;
3. fresh prospective confirmation from goldsharp closed bars;
4. explicit audit record authorizing a new exploration batch.

A separate research branch requires explicit user authorization, remains audit-only, and must not modify the frozen nine.

## Fixed period contract

- 2023: exploration only
- 2024: validation only, no retune
- 2025: final test only, no retune
- 2026: diagnostic only, never retune
- fresh prospective cutoff: `2026-06-23 18:15:00` MT5 server close

Forbidden:

- changing thresholds, features, filters, direction, TP, SL, horizon, eligibility, onset, or execution after looking at 2024, 2025, or 2026;
- rescuing a failed candidate by repeated retuning on later periods;
- replacing temporal splits with random splits;
- using 2026 for model or candidate selection.

## Search multiplicity and candidate-pool rules

Before any future exploration run, freeze and record:

- full candidate pool;
- all hypotheses;
- every parameter grid;
- every seed;
- every neighborhood cell;
- every eligibility and exclusion rule;
- planned metrics;
- pass/fail gates;
- total planned search count.

After the run, preserve and report:

- every attempted rule and parameter cell;
- all failures and null results;
- all survivors;
- total search multiplicity;
- lineage relationships;
- sample counts by year;
- caveats and blockers.

Forbidden:

- reporting only the best PF, win rate, seed, neighborhood cell, or favorable year;
- dropping losing candidates from the denominator after results are known;
- changing bootstrap, stability, or neighborhood criteria after seeing results;
- treating same-lineage variants as independent confirmation;
- summing same-lineage metrics as a portfolio.

## Candidate identity

Any change to a candidate requires a new ID, including:

- threshold;
- feature;
- timeframe;
- direction;
- TP/SL;
- horizon;
- eligibility;
- exclusion rule;
- event onset;
- execution;
- time-exit rule.

The new record must preserve parent ID, exact diff, reason, date, batch, and all prior failed versions.

## Data and leakage rules

- Raw CSV `time` is bar-open time in MT5 server naive time.
- A bar is available only after open time plus timeframe duration.
- Latest CSV row is closed by contract.
- Higher-timeframe joins must be confirmed as-of joins only.
- Lookahead is forbidden.
- Future label or exit information in features is forbidden.
- Exact M1 entry availability must be enforced where required.
- Same-M1 collision priority must be frozen before evaluation.
- Source hashes and row ranges must be recorded.
- Feature formulas and warmup rules must be versioned.
- Historical `gold_v3` rows and live `goldsharp` decisions must never be mixed.
- Proxy features/results must never be presented as exact without a separate label.
- Missing rows or losing trades must never be silently excluded.

## Warmup bridge

Every row is labeled:

- `RAW_RECONSTRUCTED`
- `WARMUP_BRIDGE_EXACT`

Bridge rows:

- are historical audit rows only;
- must be reported separately;
- must not be used for exploration, tuning, model selection, cost-stress primary populations, or live decisions;
- do not establish raw-only parity.

Full raw-only parity still requires pre-2023 candles or serialized indicator state.

## Promotion gates

Required before any registration or activation:

1. frozen exploration result;
2. untouched 2024 validation;
3. untouched 2025 test;
4. raw replay or explicitly labeled bridge audit;
5. spread and slippage stress;
6. appropriate stability checks;
7. fresh prospective confirmation;
8. explicit manual promotion decision.

Automatic promotion is forbidden. Failed stages must preserve artifacts and stop; do not rescue by retuning.

## One-click workflow

The only user-facing launcher is:

`RUN_GOLD_ML_V1_NEXT.bat`

For every future phase:

1. assistant implements and commits phase Python/BAT;
2. assistant updates `config/gold_ml_v1/next_local_action.json`;
3. assistant runs syntax/governance tests where available;
4. assistant tells user only: Pull, then double-click `RUN_GOLD_ML_V1_NEXT.bat`;
5. user uploads latest summaries.

Do not give ordinary users Python, PowerShell, or long multi-argument BAT commands.

Stable dispatcher files:

- `RUN_GOLD_ML_V1_NEXT.bat`
- `scripts/gold_ml_v1/run_next_local.py`
- `config/gold_ml_v1/next_local_action.json`

Private local paths belong only in gitignored:

`config/gold_ml_v1/local_runtime_paths.local.json`

## Current dispatcher state

`next_local_action.json` is `status_only` because Batch023 verification is complete.

It must not rerun V1-V5, the ZIP replay, or begin a new exploration.

The next chat must implement cost stress first, then change action mode to BAT.

## Next phase

`COST_STRESS_RAW_RECONSTRUCTED_ONLY_REPORT_BRIDGE_SEPARATELY_THEN_FRESH_PROSPECTIVE`

Minimum requirements:

- primary population: `RAW_RECONSTRUCTED` only;
- bridge rows separate;
- spread x1.5;
- spread x2.0;
- fixed-slippage grid predeclared before execution;
- candidate IDs and lineage preserved;
- CSV/JSON and plain-text summary;
- provenance checks;
- fail closed;
- audit-only.

## Runner requirements

Every phase runner must:

- create output directories before writing;
- back up or safely replace previous outputs;
- validate required input and provenance;
- print PASS/FAIL;
- return 0 only on PASS;
- return nonzero on validation failure;
- write latest summary and error trace;
- never continue automatically into live activation.

## Forbidden actions

- rerun V1-V5;
- call ZIP replay the original generator;
- use bridge rows for live or exploration;
- retune on 2024, 2025, or 2026;
- silently alter the candidate pool;
- activate MT5, Discord, AI API, live hooks, final signals, or registration;
- leave continuation dependent only on chat history.

## Chat-length rule

Before the chat reaches its limit, update:

- `AGENTS.md`;
- `config/gold_ml_v1/current_state_snapshot_20260624.json`;
- `config/gold_ml_v1/next_local_action.json`;
- exploration guardrails if changed;
- a dated handoff file.

The final response must list exact commit SHAs.
