# GOLD_ML_V1 — Exploration Guardrails Triple Check

Date: 2026-06-25  
Mode: **AUDIT ONLY**

## Result

The exploration and continuation rules were reviewed three separate times. The first version was not sufficient because the fixed year split and search-multiplicity rules were not explicit. Those omissions are now corrected in:

`config/gold_ml_v1/exploration_guardrails_20260625.json`

## Check 1 — Periods, time and leakage

Verified and frozen:

- Raw CSV `time` is bar-open time in MT5 server naive time.
- A higher-timeframe bar is usable only after bar-open plus its timeframe duration.
- Latest CSV row is closed by contract.
- Open or not-yet-available bars are forbidden.
- Lookahead and future label/exit information in features are forbidden.
- 2023 is exploration only.
- 2024 is validation only; no retuning from its result.
- 2025 is final test only; no retuning from its result.
- 2026 is diagnostic only; never retune from it.
- Fresh prospective cutoff is `2026-06-23 18:15:00` MT5 server close.

Outcome: **PASS after restoring the missing four-period contract.**

## Check 2 — Search multiplicity, candidate pool and lineage

Verified and frozen:

- The search space and pass criteria must be declared before execution.
- Every attempted rule and parameter cell must be written to an artifact.
- Total search count and multiplicity must be reported.
- Failed cells and all survivors must remain visible; reporting only the best result is forbidden.
- Thresholds may not be changed after seeing validation, test or 2026 results.
- Cherry-picking by best PF, win rate or one favorable year is forbidden.
- New logic requires a new candidate ID.
- Parent lineage and exact change reason are mandatory.
- Candidate-pool silent addition, removal or relabeling is forbidden.
- Candidate status must be explicit: accumulated audit-only, research-only, demoted with reason, or rejected with reason.
- Same-lineage candidates are not independent edges and their metrics cannot be simply summed.

Frozen accumulated pool:

- GML1-PROV-007
- GML1-PROV-008
- GML1-WATCH-022-B
- GML1-PROV-010
- GML1-PROV-015
- GML1-PROV-020
- GML1-WATCH-021-A
- GML1-WATCH-021-B
- GML1-WATCH-021-C

Research-only, preserved with reasons:

- GML1-WATCH-014-A
- GML1-WATCH-022-A
- GML1-WATCH-023-A

No new candidate exploration may replace, alter or distract from the current nine before cost stress and fresh prospective confirmation. A separate exploration branch requires explicit user authorization and remains audit-only.

Outcome: **PASS after adding multiplicity and candidate-pool preservation rules.**

## Check 3 — One-click execution and promotion safety

Verified and frozen:

- The only user-facing launcher is `RUN_GOLD_ML_V1_NEXT.bat`.
- Current `next_local_action.json` is `status_only`; it cannot accidentally rerun old replay or begin exploration.
- A future chat must implement and commit the next phase before switching the action to BAT mode.
- The user is told only to Pull and double-click the common BAT.
- Phase runners must validate required inputs and provenance before work.
- Every runner creates output directories, safely preserves prior outputs, prints PASS/FAIL, returns 0 only for PASS, and writes a summary and error trace.
- `WARMUP_BRIDGE_EXACT` rows remain separate and can never produce live signals.
- Cost stress is mandatory before promotion.
- Fresh prospective confirmation is mandatory before registration.
- Automatic promotion and live activation are forbidden.
- MT5 orders, Discord, AI API, live hooks and final signals remain disabled.

Automated governance test:

`tests/gold_ml_v1/test_exploration_guardrails.py`

This test checks the period split, search-multiplicity rules, candidate-pool protection, governance-file references, audit-only switches and one-click handoff requirements.

Outcome: **PASS by design; CI execution must still be checked and must not be claimed until a run is observed.**

## Mandatory next-chat behavior

A new chat must read:

1. `AGENTS.md`
2. `config/gold_ml_v1/current_state_snapshot_20260624.json`
3. `config/gold_ml_v1/next_local_action.json`
4. `config/gold_ml_v1/exploration_guardrails_20260625.json`
5. this file
6. the Batch023 forensic, bridge and one-click handoffs listed in AGENTS

The new chat must not begin a fresh exploration. The next authorized phase is cost stress on `RAW_RECONSTRUCTED` rows, with `WARMUP_BRIDGE_EXACT` rows reported separately.
