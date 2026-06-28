# GML1 live-audit runtime and new-candidate-discovery handoff

Date: 2026-06-28  
Repository: `knitanr-a11y/xauusd-signal-lab`

Formal status:

`GML1_LIVE_AUDIT_4_SLEEVES_READY_P16_P19_HISTORICAL_ONLY_NEW_DISCOVERY_NEXT`

This document supersedes the 2026-06-26 Stage031 handoff and the earlier 2026-06-27 handoffs for deciding the next action. Older documents remain audit history only.

---

## 1. Mandatory read order in the next chat

1. `AGENTS.md`
2. `START_HERE_GOLD_ML_V1_NEXT_CHAT.md`
3. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GML1_LIVE_AUDIT_AND_NEW_CANDIDATE_DISCOVERY_20260628.md`
4. `config/gold_ml_v1/current_state_20260628.json`
5. `config/gold_ml_v1/next_action_20260628.json`
6. `config/gold_ml_v1/live_research_challenger/live_runtime_contract_20260628.json`
7. `config/gold_ml_v1/research_challenger/runtime_20260628/runtime_contract.json`
8. `docs/gold_ml_v1/CURRENT_GML1_HANDOFF_20260627.md`
9. `config/gold_ml_v1/mlr1_candidate_ml_eligibility_20260627.json`

Do not ask the user to paste another handoff. GitHub is authoritative.

---

## 2. Terminology that must not be mixed

There are three different sets. Do not call all of them simply “the candidates.”

### A. Historical accumulated candidate stack

The later stack file contains 15 accumulated entries and separate research watches. This is historical candidate-pool accounting. It is not the active live runtime composition.

Authoritative historical file:

`config/gold_ml_v1/provisional_candidate_stack_20260624.json`

### B. Final historical research-challenger portfolio

The reconstructed 2024–2026 historical headline used six sleeves:

1. `A_CORE` = `GML1-WATCH-022-C`
2. `B_STATE` = H1-D1 breakout plus 24-hour re-entry state machine
3. `P16` = `GML1-PROV-016-APPROX`
4. `P18` = `GML1-PROV-018-APPROX`
5. `P19` = `GML1-PROV-019-APPROX`
6. `W024A` = `GML1-WATCH-024-A`

This six-sleeve set produced the accepted historical portfolio metrics, but P16 and P19 cannot perform fresh ML inference.

### C. Current live audit runtime

Only four sleeves are enabled for new closed-bar decisions:

1. `A_CORE`
2. `B_STATE`
3. `P18`
4. `W024A`

P16 and P19 are not live-enabled.

Do not say “four candidates are active” without explaining that this means four live-capable strategy sleeves, not four currently open signals.

---

## 3. Historical research-challenger reconstruction completed in this chat

PR #63 merged the local audit-only reconstruction runtime.

Merge commit:

`d4d13616d03db0d55390a446d574771c79bd6ed6`

Key implementation:

- `scripts/gold_ml_v1/research_challenger/raw_engine.py`
- `scripts/gold_ml_v1/research_challenger/build_local_runtime.py`
- `config/gold_ml_v1/research_challenger/runtime_20260628/runtime_contract.json`
- frozen P16/P19 exclusion-time registries
- parity tests and Windows runners

Accepted historical results:

| Period | Trades | WR | PF | Total R | Max DD |
|---|---:|---:|---:|---:|---:|
| 2024 | 271 | 65.6827% | 2.4944886 | +137.4808R | 5.9077R |
| 2025 | 402 | 59.2040% | 2.0121619 | +148.0928R | 7.3846R |
| 2026 partial | 101 | 61.3861% | 1.8772867 | +42.0558R | 6.7998R |

Exact/approximate state:

- A_CORE exact
- B_STATE exact
- P18 exact
- W024A exact
- P16 pre-ML generator reconstructed; final historical output uses frozen exclusion times
- P19 pre-ML generator reconstructed; final historical output uses frozen exclusion times

P16:

- pre-ML proposals: 287
- frozen historical exclusions: 40
- retained historical rows: 247

P19:

- pre-ML proposals: 96
- frozen historical exclusions: 14
- retained historical rows: 82

---

## 4. Live audit runtime implemented in this chat

PR #64 added the persistent BAT-loop runtime.

Merge commit:

`791b9f702104c4b5ea387c85c354a6c516bc3fda`

Main launcher:

`scripts/gold_ml_v1/live_research_challenger/run_live_loop.bat`

Other operators:

- `run_live_once.bat`
- `stop_live_loop.bat`
- `reset_live_loop_lock.bat`
- `rotate_live_loop_log.bat`

Core Python modules:

- `live_data.py`
- `live_position.py`
- `live_proposals_m15.py`
- `live_proposals_h1.py`
- `live_admission.py`
- `live_records.py`
- `live_store.py`
- `live_runtime_base.py`
- `live_runtime.py`
- `run_live_once.py`

Required live CSV files in MT5 `MQL5\Files`:

- `goldsharp_m1.csv`
- `goldsharp_m5.csv`
- `goldsharp_m15.csv`
- `goldsharp_h1.csv`
- `goldsharp_h4.csv`
- `goldsharp_d1.csv`

The CSV latest-row contract is closed. Do not reinterpret the last valid row as open or as-of unfinished.

### Enabled live sleeves

| Component | Candidate ID | Direction | Source / HTF | Target | Horizon |
|---|---|---|---|---:|---:|
| A_CORE | GML1-WATCH-022-C | LONG | M15 / H4 | 1.0R | 6h |
| B_STATE | GML1-H1D1-STATEFUL-REENTRY24-C | LONG | H1 / D1 | 1.0R | 48h |
| P18 | GML1-PROV-018-APPROX | LONG | M15 / H4 | 1.0R | 12h |
| W024A | GML1-WATCH-024-A | SHORT | M15 / H4 | 1.5R | 6h |

### Runtime position semantics

- one open parent position per sleeve
- exact M1 entry row required
- same-M1 target/protective collision resolves protective first
- LONG uses ask entry and bid touches/exits
- SHORT uses bid entry and reconstructed ask touches/exits
- wall-clock horizon
- OPEN / TP / SL / TIME tracking
- first run is `INITIALIZED_NO_BACKFILL`
- no old candidate notification on initialization

### Runtime outputs

`outputs/gold_ml_v1/live_research_challenger/`

- `live_state.json`
- `live_candidates.csv`
- `live_candidates.jsonl`
- `live_audit.jsonl`
- `latest_status.json`
- `live_loop.log`
- `live_loop.previous.log`
- `run_live_once_last.log`

### Safety controls

- `audit_only = true`
- `final_signal = false`
- `discord = false`
- `mt5_order = false`
- `p16_live = false`
- `p19_live = false`

---

## 5. Performance and delayed-write fixes completed in this chat

PR #65 optimized input handling and hardened timeframe synchronization.

Merge commit:

`28524a651713ae63b0ef1014b58ae8c1746b0436`

Changes:

- BAT performs a lightweight file-signature probe every 2 seconds.
- Heavy pandas/runtime processing starts only if at least one CSV changed.
- Unchanged weekend data does not trigger full recalculation.
- M1 is read from the required file tail instead of parsing the full history.
- M5 reads only the latest rows because it is not a rule input for the four enabled sleeves.
- M15/H1/H4/D1 retain full-history feature calculation; candidate formulas were not simplified.
- File mutation during probe/read results in `DEFERRED`; cursors do not advance.
- Exact M1 decision-entry row is required.
- An actual M15 four-hour boundary waits for its H4 row.
- An actual H1 daily boundary waits for its D1 row.
- Missing calendar boundaries across weekend gaps do not create false waits.

Observed old Sunday baseline:

- unchanged run duration: approximately 3.81–4.12 seconds
- average: approximately 3.895 seconds

Observed M1 input optimization:

- full M1 parse of about 1.225 million rows: approximately 0.915 seconds
- required 12,000-row tail parse: approximately 0.019 seconds
- tail rows matched the full reader at the compared end of file

### M1-first / M15-late behavior

If M1 is written first and M15 is written later:

1. M1 change is observed.
2. M15 cursor does not advance because no new M15 source row exists.
3. Existing open positions may still update from M1.
4. When M15 later changes, every M15 row after the cursor is processed in time order.
5. Existing exact M1 entry rows are then available.
6. No delayed M15 proposal is silently skipped.

If M15 never appears, the runtime does not synthesize M15 from M1.

---

## 6. Polling drift fix completed in this chat

PR #66 removed completion-based cadence drift.

Merge commit:

`9c2f362a423856ce8bd245042e4cb97501699bb2`

Old behavior:

- run processing
- then wait 60 seconds
- next start interval = processing duration + 60 seconds

Observed old interval:

- average processing: approximately 3.895 seconds
- average start interval: approximately 63.929 seconds
- cumulative drift across 30 starts: approximately 113.94 seconds

Current behavior:

- probe is aligned to absolute wall-clock 2-second boundaries
- processing duration is not added to the next interval
- missed boundaries are skipped
- runtime resumes at the next wall-clock boundary

Example:

`12:00:00, 12:00:02, 12:00:04, ...`

not:

`previous completion + 2 seconds`

---

## 7. Live runtime verification completed and remaining operational gap

Historical replay verification recorded:

- A_CORE: 6 known 2026 trades matched decision time, exit time and R
- B_STATE: 4 matched
- P18: 2 matched
- W024A: 2 matched
- initialization emitted zero historical candidates
- second unchanged run emitted zero duplicates

Verification file:

`config/gold_ml_v1/live_research_challenger/live_runtime_verification_20260628.json`

Remaining operational gap:

- the final PR #65/#66 code has not yet been confirmed from user-uploaded output during a normal market-open period
- Sunday 2026-06-28 had no new candles
- do not claim market-open prospective validation has passed

User-PC operation after pulling main:

1. stop any older loop with `stop_live_loop.bat`
2. Fetch/Pull main
3. start `run_live_loop.bat`
4. do not delete `live_state.json` or `live_candidates.csv`
5. confirm the banner contains `wall-clock anchored`

---

## 8. P16/P19 recovery investigation — final conclusion

The user searched the past chat. The following were not recovered:

- P16/P19 trained model files
- scaler/preprocessor
- original feature order
- full score registry
- numerical P16 bottom-10-percent threshold
- numerical P19 lower-support boundary
- original training script
- original inference script

The final manifest records candidate-local model artifacts as absent and fresh inference disabled.

What remains:

- reconstructed pre-ML candidate generators
- later fixed compound-loss rules
- frozen historical REJECT decision-time lists
- historical retained/excluded outputs
- text saying P16 rejected validation-score bottom 10 percent
- text saying P19 rejected outside the lower validation support boundary

Frozen exclusion files:

- `config/gold_ml_v1/research_challenger/runtime_20260628/registries/p16_exclusions_a.csv`
- `config/gold_ml_v1/research_challenger/runtime_20260628/registries/p16_exclusions_b.csv`
- `config/gold_ml_v1/research_challenger/runtime_20260628/registries/p19_exclusions.csv`

Current historical reconstruction uses:

`pre-ML proposal decision_time minus frozen exclusion decision_time = retained historical row`

It does not calculate fresh scores.

Final policy:

- P16/P19 may remain historical comparison sleeves.
- Frozen exclusion times may be used only to reconstruct historical results.
- P16/P19 fresh inference remains forbidden.
- Do not substitute ML-04, MLR1 or any unrelated model.
- Do not call a new model “recovered P16” or “recovered P19.”

---

## 9. Historical impact of P16/P19 absence

A chat-side recomputation from the final trade registry produced the following comparison. Treat this as planning context; create a committed standalone verification artifact before using it as a promotion decision.

| Metric | Historical six-sleeve portfolio | Four sleeves without P16/P19 | Change |
|---|---:|---:|---:|
| Trades | 774 | 445 | -329 (-42.5%) |
| Win rate | 61.76% | 65.62% | +3.86 points |
| PF | 2.1446 | 2.1661 | +0.0215 |
| Total R | +327.63R | +182.78R | -144.85R (-44.2%) |
| Max DD | 7.38R | 5.95R | improved by 1.43R |

Interpretation:

- removing P16/P19 does not reduce historical quality ratios
- it substantially reduces trade count and total historical R
- replacement/diversification research is important

Do not infer that the missing model would reproduce future performance.

---

## 10. MLR1 work already completed — do not repeat ML-05A v2

The earlier MLR1 program already completed more than the stale ML05A handoff implied.

Completed foundations:

- ML-00 design contract
- ML-01 raw/time audit
- ML-02 causal feature engine
- ML-03 exact-M1 label engine
- ML-04 direct all-M15 diagnostic
- ML-05A label-free candidate density v1
- ML-05A density-only v2 for MLC-002, MLC-004 and MLC-005
- accepted MLC-001, MLC-003 and MLC-006 v1 definitions retained
- later event-discovery, proposer and challenger research through PR #58

PR #41 already froze density-only v2. Do not restart ML-05A v2 as if it were pending.

The MLR1 eligibility contract remains useful:

- deterministic proposal generator committed to GitHub
- causal closed-bar inputs only
- historical/live reproducibility
- definition frozen before labeled performance inspection
- raw proposals saved before one-position/outcome filtering
- no nonreproducible candidate in model training or live inference

Authoritative eligibility file:

`config/gold_ml_v1/mlr1_candidate_ml_eligibility_20260627.json`

---

## 11. Next task — new candidate discovery, not P16/P19 retraining

The user explicitly wants to restart candidate exploration if exact P16/P19 recovery is impossible. Recovery is now considered impossible with the available artifacts.

Next formal research stage:

`GML1_NEW_INDEPENDENT_CANDIDATE_DISCOVERY_V1_AUDIT_ONLY`

### Objective

Find new reproducible independent sleeves that can restore part of the lost trade count and total R without pretending to recover P16/P19.

Priority roles:

1. independent LONG continuation/retest structures
2. independent SHORT breakdown/retest or exhaustion structures
3. candidates with low decision-time and holding-interval overlap versus A_CORE, B_STATE, P18 and W024A
4. candidate definitions usable identically in historical and future `goldsharp_*.csv`

### Required sequence

1. Freeze the current four-live-sleeve benchmark and the six-sleeve historical reference.
2. Commit a new discovery contract before inspecting candidate performance.
3. Build causal deterministic proposal grammars from authorized GML1 features only.
4. Save every raw proposal before deduplication, one-position or outcome filtering.
5. Perform label-free density, direction, time-of-day, regime and overlap audits.
6. Freeze candidate definitions and hashes.
7. Only then join frozen ML-03 labels/outcomes.
8. Evaluate using expanding purged walk-forward splits and frozen Strong/Extreme costs.
9. Compare incremental portfolio value against the current four live-capable sleeves.
10. If a meta-model is trained, persist model, scaler/pipeline, exact feature order, calibration, thresholds and every proposal score.
11. Keep all new outputs audit-only until prospective gates pass.

### Candidate grammar starting areas

These are search themes, not pre-approved candidates:

LONG:

- causal breakout then frozen-level retest
- Donchian breakout then shallow reclaim
- volatility compression release then first pullback
- EMA-band recovery then continuation
- failed downside break followed by structure recovery

SHORT:

- causal support breakdown then frozen-level retest
- Donchian breakdown then EMA rejection
- volatility expansion with weak rebound
- failed upside break followed by breakdown
- high-volatility exhaustion reversal independent of W024A

Use symmetric LONG/SHORT definitions where technically meaningful. Do not force symmetry if market microstructure makes the event definition invalid, but document any asymmetry before labels are inspected.

### First deliverables in the next chat

1. `config/gold_ml_v1/new_candidate_discovery_v1_contract_20260628.json`
2. candidate-family specification document
3. deterministic raw proposal builder
4. label-free density and overlap audit
5. tests proving closed-bar causality and historical/live parity

Do not start with model training.

---

## 12. Absolute prohibitions

- GOLD_ML_V1 only.
- Do not read or use GOLD V2, old GOLD, DISC8 or Stage41.
- Do not use legacy models/features as fallback.
- Do not run, repair, recreate or rescue Batch024.
- Do not run, repair, recreate, rescue or use `GML1-PROV-030-A`.
- Do not use ML-04 as a P16/P19 substitute.
- Do not use frozen P16/P19 decision-time exclusions for future decisions.
- Do not inspect labels/performance while adjusting proposal density.
- Do not silently retune on 2025 or 2026.
- Do not alter the current live runtime while starting discovery unless fixing a demonstrated runtime defect.
- No automatic retraining within an immutable model version.
- No final signal, Discord or MT5 order.
- No automatic promotion or registration.

---

## 13. Time and data contracts

- CSV time is MT5 server naive bar-open time.
- Do not convert decision logic to JST.
- Latest valid CSV row is closed by contract.
- M15 decision time = bar-open + 15 minutes.
- H1 decision time = bar-open + 1 hour.
- Exact M1 bar-open at decision time is required for entry/outcome evaluation.
- Higher-timeframe joins use only bars closed at or before decision time.
- Same-M1 target/protective collision resolves protective first.
- No next-M1 fallback.
- No future-confirmed ZigZag or repainting feature.

Historical research source:

`C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\gold_v3_2023_2026`

Future live source:

`C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files`

Only Files-root `goldsharp_*.csv` may be used by the live adapter.

---

## 14. Key merged PRs and commits from this chat

| PR | Purpose | Merge commit |
|---|---|---|
| #63 | local historical research-challenger runtime | `d4d13616d03db0d55390a446d574771c79bd6ed6` |
| #64 | persistent audit-only live BAT loop | `791b9f702104c4b5ea387c85c354a6c516bc3fda` |
| #65 | fast file probe, M1 tail read, delayed-write synchronization | `28524a651713ae63b0ef1014b58ae8c1746b0436` |
| #66 | wall-clock-anchored polling; remove completion drift | `9c2f362a423856ce8bd245042e4cb97501699bb2` |

---

## 15. Required first response in the next chat

After reading the mandatory files, state that:

- the four-sleeve audit-only live runtime is implemented
- P16/P19 are historical-only because fresh ML artifacts are unrecoverable
- the final live runtime still needs user-PC market-open observation after PR #65/#66
- ML-05A density v2 is already completed and must not be repeated
- the next task is `GML1_NEW_INDEPENDENT_CANDIDATE_DISCOVERY_V1_AUDIT_ONLY`
- candidate definitions and density must be frozen before labels are inspected
- no signal, Discord or MT5 order is authorized

Then begin by auditing the current repository state and drafting the new discovery contract. Do not ask the user to paste older handoffs or repeat known paths.
