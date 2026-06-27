# GML1-MLR1 — comprehensive next-chat handoff

Date: 2026-06-27  
Current status: `ML05A_V1_LABEL_FREE_DENSITY_AUDITED_PARTIAL_PASS_V2_REQUIRED_AUDIT_ONLY`

This document is the primary handoff for the next chat. It records the machine-learning rebuild performed in this chat, the change to candidate-driven meta-learning, the latest label-free proposal-density result, the immediate next task, and the final objective of automated trading.

---

## 1. Final objective

The final objective is an automated XAUUSD trading system in which:

1. deterministic specialist candidates detect interpretable market structures,
2. a machine-learning meta-model evaluates the current market environment for each candidate proposal,
3. the model estimates calibrated Strong-cost expected value or outcome probabilities,
4. deterministic portfolio and risk rules arbitrate conflicts and enforce one-position and execution limits,
5. the system first runs in audit-only shadow mode on live `goldsharp_*.csv` closed-bar data,
6. only after prospective gates pass, a separately authorized production stage may send MT5 orders automatically.

The intended architecture is:

```text
Files-root goldsharp closed candles
    -> causal feature engine shared with historical research
    -> deterministic specialist candidate proposal generators
    -> candidate_id + candidate_family + market-regime features
    -> calibrated candidate meta-model
    -> Strong-cost EV and pass/skip ranking
    -> deterministic conflict, one-position and risk arbitration
    -> audit-only shadow
    -> prospective validation
    -> separately authorized MT5 automatic execution
```

The machine-learning role is **not** to invent trades directly from every M15 bar. Its primary role is to decide which specialist candidate proposals have sufficiently high expected value in the current regime.

---

## 2. Absolute boundaries

- Work only in `GOLD_ML_V1 / GML1-MLR1`.
- Do not reuse old Stage2 weights, scalers, thresholds or feature contracts.
- Do not use GOLD V2, old GOLD, DISC8 or Stage41 as a fallback or training source.
- The historical candidate stack is not deleted or rewritten by the ML eligibility decision.
- Candidate exclusion here means exclusion from MLR1 model inputs only.
- Audit-only remains ON.
- No model is promoted.
- No shadow signal is active.
- No final signal, MT5 order or Discord output is active.
- Do not join candidate proposals to labels until the ML-05A density gate is resolved.
- Do not inspect candidate performance when adjusting proposal density.
- Do not silently mix historical and live data.
- Do not automatically fall back between data-source roles.
- No automatic retraining within an immutable model version.

Retired or closed items:

- `GML1-WATCH-031-A`: retired; never reuse.
- `GML1-PROV-030-A`: rejected and closed; do not repair, recreate or use as fallback.

---

## 3. Data-source separation

### Historical research, training and backtest source

```text
C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\gold_v3_2023_2026
```

Expected files:

- `gold_v3_2023_2026_m1.csv`
- `gold_v3_2023_2026_m15.csv`
- `gold_v3_2023_2026_h1.csv`
- `gold_v3_2023_2026_h4.csv`
- `gold_v3_2023_2026_d1.csv`

This source is allowed for fixed-snapshot research, feature construction, labels, walk-forward development and calibration only.

### Future live, shadow and operational source

```text
C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files
```

Only Files-root:

```text
goldsharp_*.csv
```

may be used by the future live adapter. The `gold_v3_2023_2026` subdirectory must be excluded from live discovery.

The live files must not be used to retune MLR1-v1 features, candidate thresholds, model hyperparameters, calibration or policy thresholds.

Authoritative source-role contract:

`config/gold_ml_v1/mlr1_data_source_role_contract_20260627.json`

---

## 4. Time, causality and execution semantics

- CSV `time` is MT5 server naive bar-open time.
- The latest CSV row is closed by contract.
- M15 decision time is M15 bar-open plus 15 minutes.
- Exact M1 bar-open at decision time is mandatory where entry or label evaluation is required.
- Missing exact M1 means skip; no next-M1 fallback.
- H1, H4 and D1 joins may use only bars whose close time is at or before the decision.
- Raw OHLC is bid.
- LONG entry is bid open plus contemporaneous spread.
- LONG touches and exits use bid.
- SHORT entry is bid open.
- SHORT touches and exits use reconstructed ask = bid plus contemporaneous spread.
- Same-M1 target/protective collision resolves protective first.
- Wall-clock horizons are enforced.
- Rolling historical baselines use lagging or `shift(1)` where required.
- No future-confirmed ZigZag or repainting swing feature is allowed.

---

## 5. Authoritative raw snapshot hashes

The initial ML-00 H1 and D1 hash strings contained transcription errors. The correction file is authoritative:

`config/gold_ml_v1/mlr1_stage_ml00_correction_001_20260627.json`

Authoritative SHA256 values:

- M1: `dec61b435ceb1df687baced57862de214793e0270e30c67d84f510f9f119b9d2`
- M15: `e327bedd180dae6429ed658ea714bc1229fb026262124248cdd5fff38fdeaa28`
- H1: `fb9d4ad228c02383a14ac86309f7306a799b0ef8d076f015a72b70daaddafc4a`
- H4: `5cd0d4427c752bd3feffd17b91fbd1ed3cd35ee5210887fa1726f01184367913`
- D1: `58d9b8e6716b3dedf4d310b3de5a914ab062c50578bae54dc85a2c8fddf689f6`

---

## 6. Work completed in this chat

### ML-00 — design contract

A new ML lane was created independently of old Stage2.

Frozen items include:

- fixed historical snapshot,
- time and bid/ask semantics,
- exact-M1 rules,
- 6-hour label geometry,
- Strong and Extreme cost scenarios,
- causal feature boundaries,
- expanding purged walk-forward folds,
- calibration and policy rules,
- shadow and prospective gates.

Primary design contract:

`config/gold_ml_v1/mlr1_stage_ml00_design_contract_20260627.json`

### ML-01 — raw-data and timestamp audit

Completed:

- source identity,
- schema and ordering,
- OHLC validity,
- aggregation parity,
- exact-M1 gap behavior,
- closed-higher-timeframe causality.

### ML-02 — common causal feature engine

Implemented files:

- `scripts/gold_ml_v1/mlr1/build_features.py`
- `config/gold_ml_v1/mlr1_feature_contract_v1_20260627.json`
- `tests/gold_ml_v1/test_mlr1_features.py`
- `scripts/gold_ml_v1/mlr1/run_build_features.bat`

Accepted output:

- eligible rows: `74,168`
- model features: `161`
- first decision: `2023-04-18 01:15:00`
- last decision: `2026-06-19 19:45:00`
- feature registry SHA256: `81a3c33c61d07eebbb13514965539a05d5f150e2ce521e613e2089be01d94a2b`

The deterministic gzip feature registry matched exactly between the container and Windows 11 / Python 3.12 / NumPy 2.2.6 / pandas 2.2.3.

The auxiliary feature-columns JSON has an LF/CRLF byte-hash difference only; this is not a feature-content mismatch.

### ML-03 — exact-M1 label engine

Implemented files:

- `scripts/gold_ml_v1/mlr1/build_labels.py`
- `config/gold_ml_v1/mlr1_label_contract_v1_20260627.json`
- `tests/gold_ml_v1/test_mlr1_labels.py`
- `scripts/gold_ml_v1/mlr1/run_build_labels.bat`

Frozen label:

```text
MLR1_LABEL_6H_TP1P5_SL1P0_ATR14
```

- LONG and SHORT evaluated independently,
- target = `1.5 ATR`,
- protective = `1.0 ATR`,
- horizon = `6 wall-clock hours`,
- classes = TARGET / PROTECTIVE / TIME,
- protective M1-open gaps fill at the adverse open,
- unresolved snapshot-tail rows are excluded.

Accepted output:

- resolved direction labels: `148,317`
- LONG: `74,157`
- SHORT: `74,160`
- label registry SHA256: `c897a00905ca3edc47eff29a159beff21e1c1aafc66c6c41558ba3dfd2a0d7ed`

The label registry matched exactly between the container and the user's Windows environment.

### ML-04 — direct all-M15 baseline diagnostic

ML-04 evaluated every eligible M15 decision directly. This was useful as a diagnostic but is **not the final system architecture**.

Models:

- unconditional class rate,
- unconditional Strong-R mean,
- always-trade one-open,
- multinomial logistic outcome model,
- Ridge Strong-R regression.

Walk-forward:

- four expanding folds,
- six-hour purge and embargo,
- validation-only hyperparameter and policy-threshold selection,
- no test retuning.

Key result:

- always-trade LONG and SHORT were strongly negative,
- all LONG linear lanes were rejected,
- Ridge was rejected,
- SHORT multinomial logistic showed ranking evidence but was not shadow-ready,
- no ML-04 policy passed the frozen shadow gate.

Best SHORT diagnostic examples:

- Standard: 335 trades, Strong total `+41.31R`, Strong PF `1.223`, Extreme total `+28.74R`.
- High coverage: 567 trades, Strong total `+57.80R`, Strong PF `1.182`, Extreme total `+33.56R`.

Reasons not to promote:

- F2 was negative,
- F4 supplied more than 65% of positive-fold R,
- Brier skill was negative in all fold/direction comparisons,
- raw probabilities were not calibrated,
- session features were too influential.

Authoritative audit:

`config/gold_ml_v1/mlr1_stage_ml04_result_audit_20260627.json`

Interpretation:

The market-environment features contain ranking information, especially for SHORT, but direct every-M15 signal creation is unstable and does not match the desired candidate-driven architecture.

---

## 7. Candidate-driven machine-learning pivot

The user clarified the intended design:

> Specialist candidates create proposals; machine learning judges the market situation and selects only candidates with high expected value.

This is now the primary architecture.

A meta-model training row will ultimately represent one candidate proposal:

```text
decision_time
candidate_id
candidate_family
direction
proposal_strength
161 causal market-environment features
ML-03 outcome and Base/Strong/Extreme R
```

The model must learn concepts such as:

- which candidate works in high or low ATR,
- trend alignment or countertrend risk,
- spread and volume state,
- time/session dependency,
- candidate-specific regime interaction,
- which candidate to prefer when multiple proposals occur together.

---

## 8. Existing candidate-stack ML eligibility

Authoritative file:

`config/gold_ml_v1/mlr1_candidate_ml_eligibility_20260627.json`

### Sixteen candidates excluded from MLR1 model use

These lack a committed exact raw proposal generator plus proposal-level parity package satisfying the new meta-model contract:

- `GML1-WATCH-024-A`
- `GML1-WATCH-026-B`
- `GML1-WATCH-027-B`
- `GML1-WATCH-028-B`
- `GML1-WATCH-029-A`
- `GML1-WATCH-030-A`
- `GML1-WATCH-025-A`
- `GML1-WATCH-026-A`
- `GML1-WATCH-027-A`
- `GML1-WATCH-028-A`
- `GML1-WATCH-032-A`
- `GML1-WATCH-033-A`
- `GML1-WATCH-034-A`
- `GML1-WATCH-034-B`
- `GML1-WATCH-034-C`
- `GML1-WATCH-036-A`

They are excluded from training, validation, test, calibration, live inference and fallback.

### Nine exact-replay candidates retained as benchmark-only

- `GML1-PROV-007`
- `GML1-PROV-008`
- `GML1-WATCH-022-B`
- `GML1-PROV-010`
- `GML1-PROV-015`
- `GML1-PROV-020`
- `GML1-WATCH-021-A`
- `GML1-WATCH-021-B`
- `GML1-WATCH-021-C`

These are not primary training candidates because all are LONG and collapse into two nested, historically tuned lineages. They remain available only for benchmark and later ablation.

The historical candidate stack itself remains unchanged.

---

## 9. New ML-native candidate families

A new outcome-free primary pool was created before inspecting labels or candidate performance.

Contract:

`config/gold_ml_v1/mlr1_ml_native_candidate_contract_v1_20260627.json`

Generator:

`scripts/gold_ml_v1/mlr1/build_ml_native_candidate_proposals.py`

Tests:

`tests/gold_ml_v1/test_mlr1_ml_native_candidates.py`

Windows runner:

`scripts/gold_ml_v1/mlr1/run_build_ml_native_candidate_proposals.bat`

Six symmetric families, twelve candidates:

1. `MLC-001` — higher-timeframe trend pullback resumption.
2. `MLC-002` — low-volatility Bollinger breakout.
3. `MLC-003` — high-volatility momentum expansion.
4. `MLC-004` — low-ADX range rejection.
5. `MLC-005` — high-volatility exhaustion reversal.
6. `MLC-006` — multi-timeframe rolling breakout.

Each family has `-L` and `-S` variants.

Proposal rules:

- state false-to-true onset,
- exact preceding M15 required for previous-value conditions,
- time gap resets previous state,
- raw proposals preserved before one-open,
- no cross-candidate dedup,
- no outcome filtering,
- all 161 environment features retained.

---

## 10. Latest ML-05A label-free density result

Authoritative audit:

`config/gold_ml_v1/mlr1_stage_ml05a_density_audit_v1_20260627.json`

Proposal output:

- rows: `3,180`
- columns: `166`
- candidates: `12`
- unique decisions: `3,002`
- decisions with multiple candidates: `178`
- maximum candidates at one decision: `2`
- LONG proposals: `2,118`
- SHORT proposals: `1,062`
- proposal registry SHA256: `d47a745402f4be01d7be5e1a6e830f33515e7317768363d745cff8ea09fb8219`
- labels joined: `false`
- performance calculated: `false`

Density gate:

- minimum 100 proposals per candidate,
- maximum 5,000 proposals per candidate,
- at least three calendar years.

### Accepted and frozen v1 candidates

| Candidate | Direction | Proposals | Years |
|---|---|---:|---|
| GML1-MLC-001-L | LONG | 1,093 | 2023–2026 |
| GML1-MLC-001-S | SHORT | 416 | 2023–2026 |
| GML1-MLC-003-L | LONG | 390 | 2023–2026 |
| GML1-MLC-003-S | SHORT | 249 | 2023–2026 |
| GML1-MLC-006-L | LONG | 454 | 2023–2026 |
| GML1-MLC-006-S | SHORT | 222 | 2023–2026 |

Do not change these v1 definitions based on later results.

### Failed v1 candidates requiring a new version before labels

| Candidate | Direction | Proposals | Years | Failure |
|---|---|---:|---|---|
| GML1-MLC-002-L | LONG | 93 | 2023–2026 | below 100 |
| GML1-MLC-002-S | SHORT | 78 | 2023–2026 | below 100 |
| GML1-MLC-004-L | LONG | 35 | 2023–2026 | below 100 |
| GML1-MLC-004-S | SHORT | 52 | 2023–2026 | below 100 |
| GML1-MLC-005-L | LONG | 53 | 2023–2026 | below 100 |
| GML1-MLC-005-S | SHORT | 45 | 2023–2026 | below 100 |

All six have four-year coverage, so the only current failure is insufficient event density.

Do not join these v1 proposals to outcomes. Preserve their contract and registry as an audit artifact.

---

## 11. Exact next task for the new chat

The next chat must begin with **ML-05A density-only v2 work**, not model training and not label analysis.

### Step 1 — verify current artifacts

Read this handoff and the files in the read order below. Confirm the v1 proposal registry SHA:

`d47a745402f4be01d7be5e1a6e830f33515e7317768363d745cff8ea09fb8219`

### Step 2 — build a label-free condition-funnel diagnostic

For each failed family and direction:

- `MLC-002-L/S`
- `MLC-004-L/S`
- `MLC-005-L/S`

count how many rows survive after each condition, by:

- full snapshot,
- calendar year,
- direction,
- final onset conversion.

This diagnostic may read features and proposal conditions only. It must not read:

- outcome,
- Base R,
- Strong R,
- Extreme R,
- PF,
- win rate,
- drawdown,
- ML-03 label registry.

### Step 3 — create a new version for failed families

Use only the condition-funnel and density distribution to broaden the failed families. Create immutable new candidate IDs or an explicit v2 contract. Do not overwrite v1.

The objective is coverage, not historical profitability:

- 100 to 5,000 proposals per candidate,
- at least three calendar years,
- retain interpretable family identity,
- preserve LONG/SHORT symmetry as far as structurally valid,
- avoid making every bar a proposal.

Passing v1 families `MLC-001`, `MLC-003` and `MLC-006` must remain unchanged.

### Step 4 — rebuild the primary proposal pool

Create a combined primary registry containing:

- accepted v1 candidates from families 001, 003 and 006,
- accepted revised candidates from families 002, 004 and 005.

Run density, year-coverage, direction-balance and overlap checks again.

### Step 5 — only after full density acceptance, enter ML-05B

ML-05B may join proposals to the frozen ML-03 label registry using:

- `decision_time`,
- `direction`.

The candidate event registry must retain:

- candidate ID and family,
- proposal time and direction,
- proposal strength,
- all 161 market features,
- TARGET / PROTECTIVE / TIME,
- Base / Strong / Extreme R,
- exit time.

Do not apply one-open before preserving the raw labeled event registry.

---

## 12. Roadmap from the current point to automated trading

### ML-05A — candidate proposal quality and density

Current stage. Complete the label-free candidate pool without outcome leakage.

### ML-05B — candidate event registry

Join accepted proposal events to frozen ML-03 labels. Audit duplicates, direction mapping, exact row retention and candidate/event overlap.

### ML-05C — candidate-selection baselines

Compare, with the same four purged walk-forward folds:

- accept every candidate proposal,
- candidate-only historical priors learned from train only,
- candidate ID plus linear logistic outcome model,
- candidate ID plus linear Strong-R model,
- no-session-feature ablation,
- benchmark-only legacy candidates kept separate.

Test data must never select thresholds or candidate rules.

### ML-06 — nonlinear meta-model and calibrated EV

Train tabular nonlinear models on candidate events, not every M15 bar.

Required inputs:

- candidate ID,
- candidate family,
- direction,
- candidate-specific proposal strength,
- 161 causal market features.

Required evaluations:

- full feature set,
- no-server-hour ablation,
- candidate ID ablation,
- candidate-family-only variant,
- fold and regime consistency,
- Strong and Extreme cost,
- winner concentration.

Calibration uses validation data only. Output should support:

```text
P(TARGET)
P(PROTECTIVE)
P(TIME)
E[TIME_R | proposal, regime]
calibrated Strong-cost EV
```

### ML-07 — candidate arbitration and portfolio rules

When multiple proposals occur:

- compare calibrated Strong EV,
- resolve same-direction duplicates,
- resolve LONG/SHORT conflict,
- enforce one-position or explicitly frozen position limits,
- enforce spread and risk limits,
- report candidate contribution and portfolio drawdown,
- maintain fail-closed behavior.

Portfolio rules remain deterministic and versioned.

### ML-08 — frozen shadow package and live adapter

Implement a separate live adapter for Files-root `goldsharp_*.csv` only.

It must:

- use only closed rows,
- use identical causal feature and candidate logic,
- record source hashes and timestamps,
- never fall back to historical files,
- load a frozen model/calibration/policy package,
- generate audit-only shadow decisions,
- send no MT5 orders.

### ML-09 — prospective evaluation

Use only data outside the frozen development snapshot.

Minimum existing contract:

- at least six elapsed months,
- at least 100 resolved trades per direction,
- no retraining or threshold changes within the version,
- drift and candidate contribution monitoring,
- Strong and Extreme cost review.

### Production activation after ML-09

Automatic trading is the final goal, but it requires a separately committed activation stage after prospective gates pass.

That stage must include:

- explicit user authorization,
- frozen model and candidate package IDs,
- MT5 order adapter,
- maximum position and loss limits,
- spread and stale-data guardrails,
- duplicate-order prevention,
- restart and state-recovery behavior,
- kill switch,
- shadow-versus-order parity checks,
- complete order and decision audit logs,
- fail-closed handling for missing or malformed data.

No automatic order execution is authorized by the current handoff.

---

## 13. Required read order in the next chat

1. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GML1_MLR1_ML05A_DENSITY_AUDITED_20260627.md`
2. `config/gold_ml_v1/mlr1_stage_status_20260627.json`
3. `config/gold_ml_v1/mlr1_stage_ml05a_density_audit_v1_20260627.json`
4. `config/gold_ml_v1/mlr1_candidate_ml_eligibility_20260627.json`
5. `config/gold_ml_v1/mlr1_ml_native_candidate_contract_v1_20260627.json`
6. `scripts/gold_ml_v1/mlr1/build_ml_native_candidate_proposals.py`
7. `config/gold_ml_v1/mlr1_stage_ml00_design_contract_20260627.json`
8. `config/gold_ml_v1/mlr1_stage_ml00_correction_001_20260627.json`
9. `config/gold_ml_v1/mlr1_data_source_role_contract_20260627.json`
10. `config/gold_ml_v1/mlr1_user_pc_pinned_replay_acceptance_20260627.json`
11. `config/gold_ml_v1/mlr1_stage_ml04_result_audit_20260627.json`
12. ML-02 and ML-03 contracts and validation documents as needed.

---

## 14. Current controls

```text
audit_only = true
labels_joined_to_candidates = false
candidate_performance_reviewed = false
model_trained_for_candidate_meta_learning = false
model_promoted = false
shadow_ready = false
live_adapter_implemented = false
live_ready = false
final_signal = false
mt5_order = false
discord = false
```

The next chat must not skip the density-only v2 stage or begin outcome analysis on the failed v1 candidate families.
