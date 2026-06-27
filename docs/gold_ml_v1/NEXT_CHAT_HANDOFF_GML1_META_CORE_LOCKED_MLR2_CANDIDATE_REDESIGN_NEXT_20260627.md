# Next Chat Handoff — GML1 Meta Core Locked / MLR2 Candidate Redesign Next

## Start here

Repository: `knitanr-a11y/xauusd-signal-lab`

Read these first:

1. `docs/gold_ml_v1/GML1_META_MODEL_CORE_V1_LOCK_20260627.md`
2. `config/gold_ml_v1/mlr1_meta_model_core_contract_v1_20260627.json`
3. `config/gold_ml_v1/mlr1_stage_status_addendum_meta_core_locked_20260627.json`
4. `config/gold_ml_v1/mlr1_stage_status_addendum_real_live_audit_prospective_capture_20260627.json`

## Non-negotiable boundaries

- Audit-only remains active.
- No promoted model exists.
- Do not connect research fold models to live inference, shadow signals, Discord, final signal or MT5 orders.
- Do not reuse Stage2 weights, scalers, thresholds or feature contracts.
- Do not use GOLD V2, old GOLD, DISC8 or Stage41 as fallback.
- Historical `gold_v3_2023_2026` and Files-root `goldsharp_*.csv` remain separate sources.
- CSV latest row is closed by the CSV contract. Do not invent an open/as-of row.
- Preserve raw candidate events before deduplication and one-position.

## Machine-learning structure now fixed

Core ID: `GML1-META-CORE v1`

- direct Strong-R XGBoost regression;
- separate LONG and SHORT models;
- 161 causal market features plus candidate-ID one-hot;
- classifier excluded from the decision path;
- FULL versus NO_TIME chosen by validation MSE only;
- validation-only nonnegative affine calibration;
- conservative/standard/high-coverage validation thresholds;
- four fixed purged and embargoed walk-forward folds;
- raw, dedup and one-position reporting;
- fixed promotion gates;
- deployment always blocked unless a later candidate version passes every gate and receives a separate manual promotion decision.

Reference replay is exact and deterministic, but the current candidate set is not accepted. Reference conservative result is 113 trades, Strong +11.637R, PF 1.1848; it fails direction count, PF and fold-concentration gates.

## Local research implementation

After Pull origin, dependency versions can be checked with:

`scripts\gold_ml_v1\mlr1\check_mlr1_meta_model_research_deps.bat`

Pinned versions are listed in:

`scripts\gold_ml_v1\mlr1\requirements_mlr1_meta_core_v1.txt`

The reference research replay is:

`scripts\gold_ml_v1\mlr1\run_mlr1_meta_model_research.bat`

Do not ask the user to run it while candidate redesign is still being developed. Assistant-side execution comes first. The runner exists so finalized research can later be reproduced locally.

## Next stage: MLR2 candidate redesign

The old 12 candidates remain immutable historical benchmarks. Do not overwrite, rename, promote or delete them.

Create a separately versioned MLR2 candidate pool. Its first pass must be label-free and performance-blind. Prefer state-transition setups with explicit `environment -> setup -> confirmation`, rather than broad single-bar conjunctions.

Initial structural families to freeze and density-audit:

1. H1 trend pullback resumption;
2. multi-bar volatility compression breakout;
3. failed breakout reclaim/rejection;
4. breakout retest continuation;
5. high-volatility exhaustion turn.

For every LONG and SHORT candidate:

- calculate onset on the full causal feature sequence;
- target 100 to 5,000 events over at least three calendar years;
- inspect direction balance, overlap and conflicts without labels;
- freeze definitions and output SHA before joining ML-03 labels;
- only after the freeze, build raw candidate events and run `GML1-META-CORE v1` unchanged.

## New-chat opening instruction

Continue GML1 from the handoff above. First verify that Meta Core v1 files exist on main and that no deployment path is enabled. Then continue MLR2 candidate redesign with label-free density and overlap auditing. Do not change the ML core or inspect candidate outcomes until the MLR2 proposal definitions and proposal-registry SHA are frozen.
