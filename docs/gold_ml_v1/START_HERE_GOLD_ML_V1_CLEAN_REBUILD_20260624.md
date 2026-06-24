# GOLD ML V1 — Clean Rebuild Start Here

Date: 2026-06-24  
Repository: `knitanr-a11y/xauusd-signal-lab`  
Branch: `main`

Current status:

`GOLD_ML_V1_000_CLEAN_REBUILD_CONTRACT_FROZEN`

Current decision:

`START_NEW_SYSTEM_WITH_APPEND_ONLY_INDEPENDENT_CANDIDATES`

Next phase:

`GOLD_ML_V1_001_DATASET_AND_EVALUATION_CONTRACT`

Machine-readable contract:

`config/gold_ml_v1/project_contract.json`

---

## 1. This is the sole start document

For every future `GOLD_ML_V1` task, read this document first.

Do not begin by searching the repository broadly. Do not inspect prior GOLD documents, scripts, outputs, models, metrics, stages, or handoff files for context.

This document and files subsequently created inside the new `gold_ml_v1` namespace are the only project history permitted for the rebuild.

If information required for the new system is not present in the new namespace, treat it as unknown and define it from zero. Never recover it from an old GOLD source.

---

## 2. User objective — never reinterpret this

The objective is not to keep replacing one so-called main candidate.

The objective is:

1. discover multiple independently useful, high-win-rate candidates;
2. preserve every registered candidate as a separate immutable research object;
3. add new candidates beside existing candidates instead of overwriting them;
4. evaluate combinations only in a separate portfolio layer;
5. increase total opportunity by accumulating good candidates, not by silently loosening or mixing one candidate until its identity changes.

Example:

- Candidate A remains Candidate A.
- Candidate B is registered separately.
- Candidate C is registered separately.
- `A+B+C` is a portfolio, not a renamed replacement candidate.

No future stage, model, router, filter, or portfolio may redefine the historical identity or standalone metrics of A, B, or C.

---

## 3. Old GOLD sources are quarantined by policy

The old files remain physically untouched for historical preservation, but they are prohibited sources for `GOLD_ML_V1`.

Never read, search, import, compare against, inherit from, copy from, summarize, use as fallback, or use for parity:

- `docs/gold_v3/**`
- `scripts/gold_v3_runtime/**`
- `models/gold_v3/**`
- `tests/gold_v3/**`
- `FX_OUTPUTS/gold_v3/**`
- any old GOLD stage file;
- any old GOLD model, scaler, feature list, label, threshold, candidate, portfolio, metric, result, runtime state, bootstrap, journal, watch, or handoff.

Do not delete, rewrite, rename, or move those old files. They are isolated, not migrated.

An old result must not be quoted as a baseline in the new project. The new project establishes its own data, labels, models, candidates, metrics, and portfolio results from zero.

---

## 4. New namespace

All new repository work must be placed only under:

- `docs/gold_ml_v1/`
- `config/gold_ml_v1/`
- `scripts/gold_ml_v1/`
- `models/gold_ml_v1/`
- `tests/gold_ml_v1/`

All local generated data and outputs must use:

- `FX_OUTPUTS/gold_ml_v1/raw/`
- `FX_OUTPUTS/gold_ml_v1/manifests/`
- `FX_OUTPUTS/gold_ml_v1/features/`
- `FX_OUTPUTS/gold_ml_v1/models/`
- `FX_OUTPUTS/gold_ml_v1/candidates/`
- `FX_OUTPUTS/gold_ml_v1/portfolios/`
- `FX_OUTPUTS/gold_ml_v1/audits/`

Do not write new project outputs into an old output directory.

---

## 5. Fresh raw data only

The rebuild begins from freshly exported raw market data.

Old derived data and old output directories are forbidden even when the filename looks like a candle file.

Before any feature creation or machine learning:

1. export raw candles into `FX_OUTPUTS/gold_ml_v1/raw/`;
2. document symbol, timeframe, broker/server source, timezone basis, column schema, timestamp meaning, and closed-candle contract;
3. generate a hash manifest;
4. check ordering, duplicates, gaps, invalid OHLC, non-finite values, and timeframe alignment;
5. freeze a dataset ID.

Closed candles only must be used. The exact timestamp and time-basis contract must be explicitly frozen in Phase001 before training begins.

No old label, feature, model, candidate, or metric may influence raw-data acceptance.

---

## 6. Immutable IDs and append-only registry

Use independent IDs from the start:

- Dataset: `GML1-DATA-0001`
- Feature set: `GML1-FEAT-0001`
- Label: `GML1-LABEL-0001`
- Model: `GML1-MODEL-0001`
- Candidate: `GML1-CAND-0001`
- Portfolio: `GML1-PORT-0001`

IDs are never recycled.

Once a candidate is registered, the following become immutable for that candidate ID:

- source dataset and hashes;
- train, validation, test, and holdout windows;
- feature-set ID and exact ordered feature list;
- label ID and exact future-outcome definition;
- model ID and model configuration;
- direction;
- symbol and timeframes;
- decision timing;
- entry rule;
- exit, TP, SL, horizon, and intrabar priority;
- spread and cost assumptions;
- standalone one-position policy, if any;
- standalone trade registry;
- standalone metrics;
- code and configuration hashes.

Changing any of those requires a new candidate ID. Do not edit the old candidate into the new logic.

A candidate may be marked `REJECTED`, `RETIRED`, `SHADOW`, or another explicit status, but it remains in the append-only registry.

---

## 7. Candidate evaluation is independent

Each candidate must first be evaluated alone.

Candidate B must not remove, replace, reorder, or change Candidate A's standalone trades.

Candidate A's standalone metrics must not depend on whether Candidate B exists.

For every candidate, report at minimum:

- total trades;
- trade days and trades per month;
- wins, losses, and time exits separately;
- win rate with confidence interval;
- profit factor;
- total R and average R;
- maximum drawdown in R;
- largest-winner concentration;
- long/short counts;
- year, quarter, volatility, session, and regime breakdowns;
- exact standalone trade registry;
- train/validation/test/holdout separation;
- leakage and reproducibility audit.

No portfolio-level overlap result may overwrite these standalone values.

---

## 8. Portfolio layer is separate

Only registered candidates may enter portfolio research.

A combination receives a separate portfolio ID, for example:

`GML1-PORT-0001 = GML1-CAND-0001 + GML1-CAND-0002`

Portfolio rules may include:

- one-position handling;
- conflict resolution;
- direction priority;
- simultaneous-signal handling;
- capital allocation;
- exposure limits;
- candidate weighting;
- router or selector rules.

These rules apply only to the portfolio output.

They must never mutate:

- source candidate membership;
- source candidate standalone trade registries;
- source candidate standalone metrics;
- source candidate IDs.

Never call a portfolio a new version of a source candidate. Never report portfolio metrics as candidate metrics.

---

## 9. Machine-learning rebuild principles

The machine-learning system starts from zero.

Forbidden inheritance includes old:

- models and weights;
- scalers;
- feature columns;
- labels;
- thresholds;
- hyperparameters selected from prior outcomes;
- candidate rules;
- train/test periods;
- model rankings;
- performance targets derived from old results.

Before training, freeze separate contracts for:

1. raw dataset;
2. preprocessing;
3. feature generation;
4. label generation;
5. split and embargo rules;
6. model training;
7. threshold selection;
8. candidate extraction;
9. standalone evaluation;
10. final untouched holdout.

The final holdout must not be repeatedly inspected and reused for tuning.

Multiple specialist models are allowed and expected. Examples may include direction, volatility, trend, pullback, breakout, session, or other independently defined specialties, but their exact design must be established only from new-project evidence.

There is no requirement to select a single permanent main candidate.

---

## 10. Candidate discovery workflow

The default workflow is:

1. freeze a clean dataset and evaluation contract;
2. train one or more models under a frozen training contract;
3. generate candidate hypotheses without modifying already registered candidates;
4. validate each hypothesis independently;
5. register passing candidates with new candidate IDs;
6. preserve rejected candidates and rejection reasons;
7. search for additional independent candidates;
8. only after standalone registration, evaluate portfolio combinations;
9. preserve both standalone and portfolio results permanently.

A new high-win-rate candidate is an addition, not a replacement.

A weak candidate must not be hidden inside a strong portfolio to make it appear acceptable.

A strong candidate must not lose its identity because it was combined with another candidate.

---

## 11. Leakage and research discipline

All decisions at a timestamp must use only information available by that timestamp.

Future TP, SL, exit, horizon, label outcome, post-entry price movement, or future model score must not enter entry logic or candidate selection.

Train, validation, test, and final holdout roles must be explicit and non-overlapping under the frozen split contract.

Any repeated use of a test period for feature, label, threshold, candidate, or model choice must be recorded as contamination and requires a new untouched holdout.

Every generated artifact must record its source IDs and hashes.

No result is considered complete until the generated outputs have been inspected.

---

## 12. Safety state

Until explicitly authorized in a later validated phase:

- research is audit-only;
- live/final signal emission is OFF;
- MT5 automatic orders are OFF;
- Discord is OFF;
- partial close is OFF;
- automatic promotion is forbidden.

A good historical result alone never enables live operation.

---

## 13. Phase001 — next work

Next phase:

`GOLD_ML_V1_001_DATASET_AND_EVALUATION_CONTRACT`

Phase001 must create, without consulting old GOLD sources:

1. fresh-export directory and filename contract;
2. required symbols and timeframes;
3. exact CSV schema;
4. closed-candle and timestamp semantics;
5. data validation rules;
6. dataset hash manifest format;
7. train, validation, test, embargo, and final-holdout policy;
8. candidate standalone evaluation definitions;
9. append-only registry schemas for datasets, features, labels, models, candidates, and portfolios;
10. audit-only safety flags.

No model training should begin before Phase001 is frozen and audited.

---

## 14. New-chat starter prompt

Use the following instruction in a new chat:

```text
repo: knitanr-a11y/xauusd-signal-lab

This is the new GOLD_ML_V1 clean rebuild.
Read only:
- AGENTS.md
- docs/gold_ml_v1/START_HERE_GOLD_ML_V1_CLEAN_REBUILD_20260624.md
- config/gold_ml_v1/project_contract.json
- files subsequently created under the gold_ml_v1 namespace

Do not search, read, reference, compare against, inherit from, or fall back to any old GOLD source, including docs/gold_v3, scripts/gold_v3_runtime, models/gold_v3, tests/gold_v3, FX_OUTPUTS/gold_v3, or old stage artifacts.

Current status:
GOLD_ML_V1_000_CLEAN_REBUILD_CONTRACT_FROZEN

Current decision:
START_NEW_SYSTEM_WITH_APPEND_ONLY_INDEPENDENT_CANDIDATES

Next phase:
GOLD_ML_V1_001_DATASET_AND_EVALUATION_CONTRACT

The user objective is to accumulate multiple independently validated high-win-rate candidates. Never replace one candidate with another, never mix portfolio metrics into candidate metrics, and never reinterpret a portfolio as a candidate.

Work directly on main. Create the Phase001 specification, implementation, tests, and documentation inside the gold_ml_v1 namespace only. Do not begin training until the Phase001 outputs are uploaded and audited.
```

---

## 15. Foundation declaration

This document intentionally contains no inherited old performance figures, candidate definitions, model settings, or stage conclusions.

`GOLD_ML_V1` begins here.
