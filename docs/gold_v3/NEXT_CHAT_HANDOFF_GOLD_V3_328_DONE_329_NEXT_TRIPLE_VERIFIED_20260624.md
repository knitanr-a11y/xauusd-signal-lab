# GOLD V3 Next Chat Handoff — Stage328 Done / Stage329 Next / Triple Verified

Date: 2026-06-24
Repository: `knitanr-a11y/xauusd-signal-lab`
Branch: `main`
Current status: `GOLD_V3_328_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_CONTRACT_READY`
Current decision: `WAIT_FOR_FIRST_POST_FREEZE_BALANCED_OR_PREMIUM_CANDIDATE`
Next stage: `GOLD_V3_329_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_RUNTIME_AUDIT_ONLY`

This document supersedes:

`docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_328_DONE_329_NEXT_PERSISTENT_ROUTER_PROSPECTIVE_RUNTIME_20260624.md`

Use this triple-verified document as the sole next-chat handoff source.

---

## 1. Triple-verification record

### Verification pass 1 — Stage328 output consistency

Checked the uploaded Stage328 watch, frozen contract, and frozen bootstrap against each other.

Confirmed:

- watch status and decision match this document
- frozen contract SHA256 matches the watch
- frozen bootstrap SHA256 matches the watch
- bootstrap internal state SHA256 matches the contract and watch
- frozen cutoff values match
- processed candidate count is 37 everywhere
- subgroup resolved counts sum to 37
- last processed timestamps match
- last-two-R values match
- initial subgroup scores match
- post-freeze counts are all zero
- no candidate exists between the terminal historical state and the frozen cutoff

### Verification pass 2 — Project invariants and forbidden-source audit

Checked the handoff against the standing GOLD V3 rules.

Confirmed and explicitly preserved:

- GOLD V3 remains audit-only
- GOLD V2, old GOLD, DISC8, and Stage41 are prohibited
- CSV latest row remains closed by contract
- MT5 server time remains authoritative
- resolved-only router state updates
- no pending as-of PnL
- no future TP/SL/exit/horizon leakage
- parity tolerance remains `1e-12`
- Stage280 exact recovery remains blocked
- Stage281 exact model remains unchanged
- Stage292 candidate pool remains unchanged
- Stage307 registered candidate remains unchanged
- Stage314 and Stage319 contracts remain frozen/active and unchanged
- MT5 automatic orders, Discord, and partial close remain OFF
- no automatic promotion

### Verification pass 3 — Stage329 execution-continuity and ambiguity audit

Checked whether a new chat could implement Stage329 without guessing.

The following points are now made explicit to remove ambiguity:

1. exact candidate-processing order
2. distinction between router-filtered candidates and overlap-rejected/non-tradable rows
3. exact rows that may update router state
4. mutable runtime-state lineage and duplicate protection
5. frozen artifact paths and SHA checks
6. atomic state-write and restart-reconciliation requirements
7. exact first-run zero-candidate behavior
8. exact dependency files to inspect

No unresolved blocking ambiguity remains for beginning Stage329.

---

## 2. Absolute prohibitions

GOLD V3 remains audit-only.

Never read, use, reference, compare against, inherit from, or fall back to:

- GOLD V2
- old GOLD
- DISC8
- Stage41 feature-only snapshot

Those sources must not become trading, feature, fallback, health, recovery, or parity sources.

Stage280 exact recovery remains blocked. Never claim it was recovered.

Approximate/new/successor candidates remain separate research objects only.

Stage281 exact model must remain unchanged.

Do not resume Stage310 archive archaeology unless the user explicitly asks.

Do not remove candidates from Stage292 or alter Stage307 unless a later explicit validated stage authorizes it.

---

## 3. Data, time, and leakage contract

- CSV latest row is closed by contract. Never drop it as an open/as-of bar.
- MT5 server time is the time authority.
- Entry/routing decisions use only closed data known at decision time.
- Future TP, SL, exit, horizon, post-entry M1 movement, or resolution result must never enter entry/routing logic.
- Pending rows must not contain fabricated PnL or R.
- Pending source candidates do not update router state.
- Router state updates only after source candidate resolution.
- Processing must be chronological, append-only, idempotent, and duplicate-safe.
- Same M1 TP/SL touch priority is SL.
- Maximum hold is 720 minutes.
- One-position policy and no preemption remain fixed.
- Exact numeric tolerance remains `1e-12`; never weaken it.
- 2026 data inspected in Stages311 onward is display-only, not a clean holdout.
- Future prospective results may be collected, but must not train, choose, reject, rank, or retune the current router or membership thresholds.

---

## 4. Safety state that must remain unchanged

- `final_signal_enabled=True`, but final signal logic is unchanged.
- MT5 automatic order execution OFF.
- Discord OFF.
- Partial close OFF.
- No automatic production promotion.
- Stage314 prospective contract unchanged and active.
- Stage319 prospective contract unchanged and frozen forever.
- Stage328 contract and bootstrap unchanged and frozen forever.
- Stage307 registered research candidate unchanged.
- Stage292 candidate pool unchanged.

---

## 5. User working style

- Respond in Japanese.
- Work directly on `main`.
- Do not ask about branches or pull requests unless unavoidable.
- Implement the agreed next stage rather than only proposing it.
- Explain changes, reasons, results, and remaining risks.
- Give the execution BAT path in one line.
- Never claim a stage completed until uploaded outputs are inspected.

---

## 6. Condensed research progression

### Stage301–307

Stage280 exact artifact/source recovery remained blocked.

Stage307 registered candidate:

`DROP_H4+DROP_D1+ALL_TF+LTF_ONLY|ANY_P90`

Historical research reference:

- 92 trades
- PF 3.39785
- +48.622R
- DD 4.046R

Research-only and unchanged.

### Stage308–317

Stage317 selected unified source candidate:

`M5_H4|MOCHI_UNION|SHORT|RR1_5|ATR_GE_1_AND_NO_ROUND`

2024–2025 reference:

- 33 trades
- WR 57.58%
- PF 1.6958
- +11.27R
- DD 5.246R

### Stage318

Fixed profiles:

- Core: `ATR_STEADY_1_10_TO_1_45`
- Premium: `TREND_FLOW_COMPRESSION_GE_0_95`
- Balanced: `CONSENSUS_OR_ATR_STEADY_AND_RANGE`

2024–2025 references:

- Core: 24 trades, WR 62.5%, PF 1.9811, +10.748R, DD 3.173R
- Premium: 14 trades, WR 78.57%, PF 4.0792, +12.684R, DD 2.098R
- Balanced: 17 trades, WR 64.71%, PF 2.1412, +9.403R, DD 2.093R

### Stage319

Future-only dual-tier contract frozen.

Immutable cutoff:

`decision_dt > 2026-06-23 13:55:00`

Never delete, recreate, update, or move the cutoff.

### Stage320–322

Conservative shadow lane selected:

`BALANCED_OR_PREMIUM`

Stage322 2024–2025:

- 24 trades
- 16 wins / 8 losses
- WR 66.67%
- PF 2.538274
- +14.497511R
- DD 3.172719R

### Stage323

Execution-cost stress passed all gates.

At 3.0x spread cost:

- PF 2.207
- +11.49R
- DD 3.52R

### Stage324

Membership edge rotation confirmed:

- 2024–2025: Premium-involved stronger
- 2026 display-only: Balanced-without-Premium stronger

Decision:

`MEMBERSHIP_EDGE_ROTATION_DETECTED_KEEP_COMBINED_SHADOW`

### Stage325

Selected exactly one resolved-only router lead:

`RELATIVE_TRAILING_MEAN_R_N2`

Rule:

- maintain each subgroup's last two resolved spread-adjusted R values
- candidate is selected when its subgroup mean is at least the other subgroup mean
- warmup takes all until both groups have at least two resolved observations

2024–2025:

- 14 selected trades
- WR 78.57%
- PF 6.470635
- +12.551711R
- DD 1.102286R

1.5x spread cost:

- WR 78.57%
- PF 6.181
- +12.08R
- DD 1.15R

### Stage326 and Stage326A

Required reset/warmup/latency stresses passed.

Decision:

`ROUTER_OPERATIONALLY_ROBUST_BUT_REQUIRES_PERSISTENT_STATE`

Stage326 reporting-only disagreement counters were corrected by Stage326A. Core metrics and decisions were unchanged.

### Stage327

Checkpoint/restart serialization parity confirmed:

`PERSISTENT_ROUTER_STATE_CHECKPOINT_RESTART_PARITY_CONFIRMED`

- 88 restart scenarios
- 0 failures
- maximum score difference 0
- maximum selected PnL difference 0
- maximum selected R difference 0
- all terminal states equal

---

## 7. Stage328 completed and frozen

Uploaded watch status:

`GOLD_V3_328_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_CONTRACT_READY`

Decision:

`WAIT_FOR_FIRST_POST_FREEZE_BALANCED_OR_PREMIUM_CANDIDATE`

### Frozen runtime directory

Relative to the detected MT5 `MQL5\Files` directory:

`FX_OUTPUTS\gold_v3\289_training_history`

### Frozen contract

File:

`FX_OUTPUTS\gold_v3\289_training_history\stage328_persistent_router_prospective_shadow_contract.json`

SHA256:

`cfdfdd74050d33d68dcaa97dcb14b9c812f0cad00807870c922d0d13c6e050f9`

Status:

`GOLD_V3_328_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_CONTRACT_FROZEN`

### Frozen bootstrap

File:

`FX_OUTPUTS\gold_v3\289_training_history\stage328_persistent_router_bootstrap_state.json`

SHA256:

`90824803f7bb3992e73f8e0727760ffba6c31f68f77e771884a099a2cc26178e`

Internal state SHA256:

`6b165f518f67212ca217f41dc40b7e24228a5c9e3eabd2cf5a517869bb19dbaf`

Status:

`GOLD_V3_328_PERSISTENT_ROUTER_BOOTSTRAP_STATE_FROZEN`

Never modify, overwrite, delete, recreate, rename, or move either frozen file.

### Frozen cutoff

- M1 latest closed open: `2026-06-23 13:56:00`
- M1 latest closed close: `2026-06-23 13:57:00`
- M5 latest closed open: `2026-06-23 13:50:00`
- M5 latest closed close: `2026-06-23 13:55:00`
- H4 latest closed open: `2026-06-23 08:00:00`
- H4 latest closed close: `2026-06-23 12:00:00`
- candidate `decision_dt` must be strictly greater than `2026-06-23 13:55:00`

### Frozen router state

Policy:

`RELATIVE_TRAILING_MEAN_R_N2`

Lane:

`BALANCED_OR_PREMIUM`

Cost view:

`1p0x spread-adjusted R`

Processed candidates: 37

Last processed entry: `2026-06-10 19:30:00`

Last processed exit: `2026-06-10 20:23:00`

Premium-involved:

- resolved count: 23
- last two R: `1.4824067246968713`, `1.476844649654342`
- mean: `1.4796256871756066`

Balanced-without-Premium:

- resolved count: 14
- last two R: `1.4424248614869732`, `1.478948140470545`
- mean: `1.460686500978759`

Premium-minus-Balanced score difference:

`0.018939186196847535R`

Warmup is complete.

At freeze state:

- Premium candidate would be router-selected
- Balanced-without-Premium candidate would be router-filtered

This may change only after later canonical source candidates resolve.

### Current post-freeze counts

- source candidates: 0
- selected trades: 0
- resolved candidates: 0
- pending candidates: 0

### Future review gate

- at least 20 resolved source candidates
- at least 10 resolved selected trades
- selected WR at least 60%
- selected PF at least 1.25
- selected total R positive
- selected DD no more than 4R
- largest winner share no more than 35%
- state integrity required
- automatic promotion forbidden

---

## 8. Exact Stage329 candidate pipeline — do not reorder

The pipeline order is fixed to preserve historical/source parity.

### Step A — Generate raw pooled Stage317 source signals

Generate only:

`M5_H4|MOCHI_UNION|SHORT|RR1_5|ATR_GE_1_AND_NO_ROUND`

Use the exact Stage311/Stage314/Stage319 feature and signal helpers. Do not rewrite an approximate detector.

### Step B — Canonical same-decision deduplication

Pool duplicate track signals sharing the same decision time exactly as Stage319 does.

Require parity for pair, direction, direction number, signal index, ATR context, swings, ATR ratio, extension, compression, and range fields.

Create one deterministic canonical source event per exact decision time.

Stable event ID must depend only on immutable source identity plus exact `decision_dt`, never on router score, runtime state, or future result.

### Step C — Apply fixed selected-lane membership

Balanced membership:

`pooled_track_count >= 2 OR (1.10 <= atr_ratio_signal <= 1.45 AND 0.70 <= range_atr_signal <= 1.05)`

Premium membership:

`compression_ratio_signal >= 0.95`

Premium has subgroup precedence:

- Premium member -> `PREMIUM_INVOLVED`
- otherwise Balanced member -> `BALANCED_WITHOUT_PREMIUM`

Rows belonging to neither group are outside the fixed lane and must be reported, not silently converted into router observations.

### Step D — Prepare exact shadow trade

Use exact next-M5 entry alignment, structural stop, minimum 0.75 ATR risk, maximum 2.0 ATR structural risk, RR1.5 target, M1 SL-first resolution, spread adjustment, and 720-minute horizon.

### Step E — Apply source one-position portfolio policy before routing

Use Stage314's exact one-position/no-preemption portfolio policy.

This creates:

- `ACCEPTED` canonical source candidates
- `REJECTED_OVERLAP`
- `NOT_TRADABLE_YET` or invalid/risk states

Only `ACCEPTED` canonical source candidates enter the N2 router observation stream.

`REJECTED_OVERLAP`, risk-rejected, invalid alignment/gap, and not-tradable rows must be retained in raw/health outputs but must not update router history.

This distinction is essential.

### Step F — Apply N2 router to each ACCEPTED source candidate

At candidate decision time, use only the persisted state from earlier resolved ACCEPTED source candidates.

- selected by router -> selected shadow lane
- filtered by router -> source-only shadow lane

A router-filtered ACCEPTED candidate is still a valid source observation and must be shadow-resolved.

### Step G — Resolve and update state

For every ACCEPTED source candidate, regardless of router selection:

- if pending: do not update state
- after resolution: update exactly once
- increment only its assigned subgroup `resolved_count`
- append its resolved spread-adjusted R
- retain only the subgroup's last two R values
- update processed candidate/timestamp lineage

Router-filtered means filtered from selected trades, not removed from the source observation stream.

Overlap-rejected/non-tradable/invalid rows never update router state.

---

## 9. Mutable runtime-state requirements

Stage329 must never mutate the frozen bootstrap.

### First run

If no mutable runtime-state file exists:

1. verify frozen contract SHA256
2. verify frozen bootstrap SHA256
3. verify bootstrap internal state SHA256
4. create a separate mutable runtime-state file from the frozen bootstrap
5. record bootstrap/contract lineage hashes in the mutable wrapper

### Subsequent runs

If mutable runtime state exists:

- validate schema version
- validate policy and lane
- validate frozen contract/bootstrap lineage hashes
- validate subgroup counts and last-two-R lengths
- validate timestamps are monotonic
- do not recopy or reset from bootstrap
- fail closed on lineage mismatch

### Duplicate and crash protection

Mutable state must contain or be reconcilable with an append-only applied-event ledger/journal.

Required protections:

- stable source event IDs
- each canonical ACCEPTED source candidate applied to state at most once
- journal/state reconciliation before new processing
- no double state update after rerun
- no partial state advancement on crash
- atomic temporary-file write followed by replace
- preserve previous valid state if validation/write fails

Do not rely only on `processed_candidates` when stable event IDs are available.

---

## 10. Separate Stage329 outputs and metrics

Recommended outputs:

- `stage329_persistent_router_prospective_shadow_watch.json`
- `stage329_persistent_router_runtime_state.json`
- `stage329_persistent_router_state_journal.csv`
- `stage329_persistent_router_raw_signals.csv`
- `stage329_persistent_router_canonical_source_signals.csv`
- `stage329_persistent_router_source_pending.csv`
- `stage329_persistent_router_source_resolved.csv`
- `stage329_persistent_router_selected_signals.csv`
- `stage329_persistent_router_selected_pending.csv`
- `stage329_persistent_router_selected_resolved.csv`
- `stage329_persistent_router_rejected_overlap.csv`
- `stage329_persistent_router_health.csv`

Report separately:

- raw pooled signal count
- canonical deduplicated lane count
- source portfolio ACCEPTED count
- rejected-overlap count
- invalid/risk/not-tradable counts
- router-selected count
- router-filtered count
- source pending/resolved counts
- selected pending/resolved counts
- state updates applied this run
- duplicate events ignored
- current subgroup scores
- frozen/runtime lineage health
- resolved-only metrics

Never mix raw, deduplicated, source accepted, router selected, pending, resolved, and health counts.

---

## 11. First-run expected behavior

Zero candidates after the frozen cutoff is valid and must not be treated as failure.

Expected zero-candidate result:

- zero new raw/canonical/source candidates
- zero router-selected candidates
- zero pending/resolved candidates
- mutable runtime state created from bootstrap
- mutable state unchanged relative to bootstrap
- frozen contract/bootstrap unchanged
- all lineage hashes valid
- decision such as `WAIT_FOR_FIRST_POST_FREEZE_SOURCE_CANDIDATE`

Do not claim future validation from a zero-candidate run.

---

## 12. Files to read before implementing Stage329

Read these permitted GOLD V3 files first:

1. `docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_328_DONE_329_NEXT_TRIPLE_VERIFIED_20260624.md`
2. `scripts/gold_v3_runtime/models/gold_v3_328/stage328_persistent_router_prospective_shadow_spec.json`
3. `scripts/gold_v3_runtime/gold_v3_328_persistent_router_prospective_shadow_contract.py`
4. `scripts/gold_v3_runtime/bat/run_gold_v3_328_persistent_router_prospective_shadow_contract.bat`
5. `docs/gold_v3/GOLD_V3_328_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_CONTRACT_AUDIT_ONLY_20260624.md`
6. `scripts/gold_v3_runtime/gold_v3_327_persistent_router_state_checkpoint_restart_parity_audit.py`
7. `scripts/gold_v3_runtime/gold_v3_326a_router_disagreement_counter_correction_audit.py`
8. `scripts/gold_v3_runtime/gold_v3_325_asof_membership_router_replay.py`
9. `scripts/gold_v3_runtime/gold_v3_319_mochipoyo_dual_tier_prospective_watch.py`
10. `scripts/gold_v3_runtime/gold_v3_314_prospective_mochipoyo_watch.py`
11. `scripts/gold_v3_runtime/gold_v3_311_mochipoyo_and_independent_candidate_research.py`
12. `scripts/gold_v3_runtime/gold_v3_308_mochipoyo_method_walkforward.py`

Also inspect the actual Stage328 watch, contract, and bootstrap outputs in:

`FX_OUTPUTS\gold_v3\289_training_history`

Do not inspect prohibited systems.

---

## 13. Stage328 GitHub commits

- spec: `5adc5a60697046c2cac1627e9863170f2e6fe2cd`
- contract implementation: `8eb7d07e22159c32473b6e4142430da005912927`
- BAT: `61f385eda711845f14557af340a2b8d7b626c1a8`
- documentation: `d5765e8ca569049f14482e34e21a0bc150e842c0`
- original handoff: `2218ed675420dea208db1b2682e384250a0a853d`

---

## 14. New-chat starter prompt

Paste this into the next chat:

```text
repo: knitanr-a11y/xauusd-signal-lab

まず次の三重確認済み引き継ぎ文書を読み、そこに書かれた許可ファイルだけを確認して続きからお願いします。

docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_328_DONE_329_NEXT_TRIPLE_VERIFIED_20260624.md

現在Stage328まで完了しています。
status:
GOLD_V3_328_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_CONTRACT_READY

decision:
WAIT_FOR_FIRST_POST_FREEZE_BALANCED_OR_PREMIUM_CANDIDATE

Stage328 frozen contract/bootstrapは作成済みです。
削除・再作成・更新・上書き・rename・移動・cutoff変更を絶対にしないでください。

次はStage329:
GOLD_V3_329_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_RUNTIME_AUDIT_ONLY

絶対条件:
- GOLD V3はaudit-only
- GOLD V2 / 旧GOLD / DISC8 / Stage41を読まない・使わない・参照しない・fallbackにしない
- CSV最新行はclosedでopen/as-of扱いしない
- MT5 server time
- closed dataだけでentry/router判定
- future TP/SL/exit/horizon leakage禁止
- pendingにas-of PnL/Rを付けない
- state更新はcanonical ACCEPTED source candidateのresolution後だけ
- router-filtered ACCEPTED source candidateもresolution後にgroup historyを更新
- REJECTED_OVERLAP / risk rejected / invalid / not-tradable rowsはstate更新しない
- source one-position portfolio policyをrouterより先に適用
- Stage319 cutoff `decision_dt > 2026-06-23 13:55:00` 厳守
- policyは `RELATIVE_TRAILING_MEAN_R_N2` 固定
- laneは `BALANCED_OR_PREMIUM` 固定
- Premium subgroup precedence固定
- frozen bootstrapは初回だけ別mutable runtime stateへコピー
- 以後bootstrapへ戻さずstateを永続化
- stable event ID、append-only journal、duplicate防止、atomic replace必須
- parity toleranceは1e-12のまま
- 2026/future結果を選抜・再調整に使わない
- Stage280 exact recoveryはBLOCKEDのまま
- Stage281 exact modelを変更しない
- Stage292 / Stage307 / Stage314 / Stage319 / Stage328を変更しない
- MT5 orders OFF / Discord OFF / partial close OFF
- automatic promotion禁止

GitHub mainへStage329本体、BAT、仕様書を直接コミットし、実行用BATを1行で示してください。
日本語で変更理由、監査結果、残るリスクを説明してください。
```
