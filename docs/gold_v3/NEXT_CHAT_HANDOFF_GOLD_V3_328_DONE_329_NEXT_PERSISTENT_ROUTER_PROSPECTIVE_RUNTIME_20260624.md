# GOLD V3 Next Chat Handoff — Stage328 Done / Stage329 Next

Date: 2026-06-24
Repository: `knitanr-a11y/xauusd-signal-lab`
Current status: `GOLD_V3_328_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_CONTRACT_READY`
Next stage: `GOLD_V3_329_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_RUNTIME_AUDIT_ONLY`

## 1. Absolute prohibitions

GOLD V3 remains audit-only.

Never read, use, reference, compare against, inherit from, or fall back to:

- GOLD V2
- old GOLD
- DISC8
- Stage41 feature-only snapshot

Those sources are isolated and must not become trading, feature, fallback, health, or recovery sources.

Stage280 exact recovery remains blocked. Do not claim it was recovered. Approximate and successor candidates are separate research objects only.

Do not resume Stage310 archive archaeology unless the user explicitly asks.

## 2. Data and timing contract

- CSV latest row is closed by contract. Do not remove it as open or as-of.
- MT5 server time is the time authority.
- Entry decisions use only information known from closed candles at decision time.
- Future TP, SL, exit, horizon, or post-entry information must never enter entry filtering or routing.
- Pending candidates have no as-of PnL and do not update router state.
- Only resolved candidates update state.
- Router-excluded candidates still update their subgroup history after their own shadow result resolves.
- All processing must be chronological, append-only, idempotent, and duplicate-safe.
- Same M1 TP/SL touch priority is SL.
- One-position policy, no preemption, maximum hold 720 minutes.
- Exact parity tolerance remains `1e-12`; never weaken it.
- 2026 data inspected in Stages311 onward is display-only, not a clean holdout. Never use it to train, choose, reject, rank, or retune a 2026-test model.

## 3. Safety state that must remain unchanged

- `final_signal_enabled=True`, but final signal logic is unchanged.
- MT5 automatic order execution OFF.
- Discord OFF.
- Partial close OFF.
- No automatic production promotion.
- Stage314 frozen prospective contract remains unchanged and active.
- Stage319 frozen prospective contract remains unchanged forever.
- Stage307 registered research candidate remains unchanged.
- Stage292 candidate pool remains unchanged unless an explicit validated stage says otherwise.

## 4. User working style

- Respond in Japanese.
- Work directly on `main`; do not ask about branches or pull requests unless necessary.
- Implement the next agreed stage rather than only proposing it.
- Explain what changed, why, result interpretation, and remaining risk.
- Give a one-line BAT path for execution.
- Do not claim completion until uploaded outputs are inspected.

## 5. Important research progression

### Stage301–307

Stage280 exact artifact/source recovery was investigated but remained blocked. Successor research was developed separately. Stage307 registered candidate:

`DROP_H4+DROP_D1+ALL_TF+LTF_ONLY|ANY_P90`

Historical research result:

- 92 trades
- PF 3.39785
- +48.622R
- DD 4.046R

This remains research-only and unchanged.

### Stage308–317

Mochipoyo methodology and independent candidate sweeps were implemented, replayed, consolidated, and audited. Stage317 selected unified source:

`M5_H4|MOCHI_UNION|SHORT|RR1_5|ATR_GE_1_AND_NO_ROUND`

2024–2025 reference:

- 33 trades
- WR 57.58%
- PF 1.6958
- +11.27R
- DD 5.246R

### Stage318

High-confidence profiles were fixed:

- Core: `ATR_STEADY_1_10_TO_1_45`
- Premium: `TREND_FLOW_COMPRESSION_GE_0_95`
- Balanced: `CONSENSUS_OR_ATR_STEADY_AND_RANGE`

Key 2024–2025 references:

- Core: 24 trades, WR 62.5%, PF 1.9811, +10.748R, DD 3.173R
- Premium: 14 trades, WR 78.57%, PF 4.0792, +12.684R, DD 2.098R
- Balanced: 17 trades, WR 64.71%, PF 2.1412, +9.403R, DD 2.093R

### Stage319

Dual-tier future-only prospective contract was frozen. Its cutoff must never move:

`decision_dt > 2026-06-23 13:55:00`

Initial Stage319 prospective counts were zero. Do not delete or recreate the contract.

### Stage320–322

Robustness and overlap audits selected the conservative shadow lane:

`BALANCED_OR_PREMIUM`

Stage322 2024–2025:

- 24 trades
- 16 wins / 8 losses
- WR 66.67%
- PF 2.538274
- +14.497511R
- DD 3.172719R

### Stage323

Execution-cost stress passed all gates. Even at 3.0x spread cost:

- PF 2.207
- +11.49R
- DD 3.52R

### Stage324

Membership edge rotation was confirmed:

- 2024–2025: Premium-involved subgroup was stronger.
- 2026 display-only: Balanced-without-Premium subgroup was stronger.

Decision:

`MEMBERSHIP_EDGE_ROTATION_DETECTED_KEEP_COMBINED_SHADOW`

### Stage325

Resolved-only as-of router search selected exactly one lead:

`RELATIVE_TRAILING_MEAN_R_N2`

The router compares each subgroup's last two resolved R values. It takes the candidate when its subgroup mean is at least the other subgroup mean. Warmup takes all until both groups have two resolved observations.

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

No production promotion was performed.

### Stage326 and Stage326A

Operational state-reset, warmup, and observation-delay stresses passed required gates. The router was classified as:

`ROUTER_OPERATIONALLY_ROBUST_BUT_REQUIRES_PERSISTENT_STATE`

Stage326 had a reporting-only disagreement-counter bug caused by `DataFrame.take` method collision. Stage326A corrected only those counters and confirmed all core metrics and decisions unchanged.

### Stage327

Checkpoint/restart state serialization parity was confirmed:

`PERSISTENT_ROUTER_STATE_CHECKPOINT_RESTART_PARITY_CONFIRMED`

Results:

- 88 restart scenarios
- 0 failures
- maximum score difference 0
- maximum selected PnL difference 0
- maximum selected R difference 0
- all terminal states equal

The minimal persistent state was proven sufficient.

## 6. Stage328 completed and frozen

Uploaded output status:

`GOLD_V3_328_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_CONTRACT_READY`

Decision:

`WAIT_FOR_FIRST_POST_FREEZE_BALANCED_OR_PREMIUM_CANDIDATE`

The Stage328 contract and bootstrap were created on the first run and are now immutable.

### Frozen contract

File:

`stage328_persistent_router_prospective_shadow_contract.json`

SHA256:

`cfdfdd74050d33d68dcaa97dcb14b9c812f0cad00807870c922d0d13c6e050f9`

Status:

`GOLD_V3_328_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_CONTRACT_FROZEN`

### Frozen bootstrap

File:

`stage328_persistent_router_bootstrap_state.json`

SHA256:

`90824803f7bb3992e73f8e0727760ffba6c31f68f77e771884a099a2cc26178e`

State SHA256:

`6b165f518f67212ca217f41dc40b7e24228a5c9e3eabd2cf5a517869bb19dbaf`

Status:

`GOLD_V3_328_PERSISTENT_ROUTER_BOOTSTRAP_STATE_FROZEN`

Never modify, delete, recreate, or move either frozen artifact.

### Frozen cutoff

- M1 latest closed open: `2026-06-23 13:56:00`
- M1 latest closed close: `2026-06-23 13:57:00`
- M5 latest closed open: `2026-06-23 13:50:00`
- M5 latest closed close: `2026-06-23 13:55:00`
- H4 latest closed open: `2026-06-23 08:00:00`
- H4 latest closed close: `2026-06-23 12:00:00`
- Prospective candidate rule: `decision_dt` strictly after `2026-06-23 13:55:00`

### Frozen router state

Policy:

`RELATIVE_TRAILING_MEAN_R_N2`

Lane:

`BALANCED_OR_PREMIUM`

Processed historical/display candidates: 37

Last processed entry: `2026-06-10 19:30:00`

Last processed exit: `2026-06-10 20:23:00`

Premium-involved:

- resolved count 23
- last two R: `1.4824067246968713`, `1.476844649654342`
- mean: `1.4796256871756066`

Balanced-without-Premium:

- resolved count 14
- last two R: `1.4424248614869732`, `1.478948140470545`
- mean: `1.460686500978759`

Initial score difference Premium minus Balanced:

`0.018939186196847535R`

Warmup is complete. At the freeze state, a Premium candidate would be selected and a Balanced-without-Premium candidate would be filtered. This can change only after later source candidates resolve.

### Stage328 current counts

- post-freeze source candidates: 0
- post-freeze selected trades: 0
- post-freeze resolved candidates: 0
- post-freeze pending candidates: 0

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

## 7. Exact Stage328 implementation files

Read these first in the next chat:

1. `docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_328_DONE_329_NEXT_PERSISTENT_ROUTER_PROSPECTIVE_RUNTIME_20260624.md`
2. `scripts/gold_v3_runtime/models/gold_v3_328/stage328_persistent_router_prospective_shadow_spec.json`
3. `scripts/gold_v3_runtime/gold_v3_328_persistent_router_prospective_shadow_contract.py`
4. `scripts/gold_v3_runtime/bat/run_gold_v3_328_persistent_router_prospective_shadow_contract.bat`
5. `docs/gold_v3/GOLD_V3_328_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_CONTRACT_AUDIT_ONLY_20260624.md`
6. `scripts/gold_v3_runtime/gold_v3_327_persistent_router_state_checkpoint_restart_parity_audit.py`
7. `scripts/gold_v3_runtime/gold_v3_319_mochipoyo_dual_tier_prospective_watch.py`

Also inspect the uploaded Stage328 watch, contract, and bootstrap outputs before implementing Stage329.

## 8. Stage329 — next task

Implement:

`GOLD_V3_329_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_RUNTIME_AUDIT_ONLY`

This should be an actual repeatable runtime/watch stage, not another contract-freeze stage.

### Required behavior

1. Verify exact SHA256 of the frozen Stage328 contract and frozen bootstrap.
2. Never rewrite the frozen contract or bootstrap.
3. On first Stage329 run only, copy the bootstrap state into a separate mutable runtime-state file.
4. On subsequent runs, load and validate the mutable runtime state instead of recopying the bootstrap.
5. Read only permitted GOLD V3 closed-candle inputs.
6. Generate the exact Stage317 source candidate strictly after the frozen cutoff:
   `M5_H4|MOCHI_UNION|SHORT|RR1_5|ATR_GE_1_AND_NO_ROUND`.
7. Apply exact membership rules:
   - Balanced: `pooled_track_count >= 2 OR (1.10 <= atr_ratio_signal <= 1.45 AND 0.70 <= range_atr_signal <= 1.05)`
   - Premium: `compression_ratio_signal >= 0.95`
   - Premium has router-group precedence.
8. Evaluate the fixed N2 router at candidate decision time using only already-resolved state.
9. Record every source candidate, including router-filtered candidates.
10. Shadow-resolve every source candidate so filtered candidates can update history after resolution.
11. Do not update state while a source candidate is pending.
12. When a source candidate resolves, update only its assigned subgroup:
    - increment resolved count
    - append resolved spread-adjusted R
    - retain only the last two R values
13. Process each candidate exactly once. Stable event IDs and duplicate checks are required.
14. State writes must be crash-safe and atomic, preferably temporary file plus replace.
15. Maintain one-position, no-preemption, M1 SL-priority, 720-minute maximum hold.
16. Pending rows must not contain fabricated PnL or R.
17. Produce separate raw/source, routed/selected, pending, resolved, state-journal, and health metrics.
18. Do not use future prospective results to retune the router or membership thresholds.
19. No automatic promotion, execution, Discord, or partial close.

### Recommended Stage329 outputs

- `stage329_persistent_router_prospective_shadow_watch.json`
- `stage329_persistent_router_runtime_state.json`
- `stage329_persistent_router_state_journal.csv`
- `stage329_persistent_router_source_signals.csv`
- `stage329_persistent_router_source_pending.csv`
- `stage329_persistent_router_source_resolved.csv`
- `stage329_persistent_router_selected_signals.csv`
- `stage329_persistent_router_selected_pending.csv`
- `stage329_persistent_router_selected_resolved.csv`

The mutable runtime-state file must never be confused with the frozen bootstrap file.

### First-run expected outcome

If no candidate exists after the frozen cutoff, Stage329 should still complete successfully with:

- zero new source candidates
- zero selected candidates
- unchanged mutable state equal to bootstrap
- valid state and source hashes
- a waiting decision such as `WAIT_FOR_FIRST_POST_FREEZE_SOURCE_CANDIDATE`

Do not treat zero candidates as failure.

## 9. Stage328 GitHub commits

- spec: `5adc5a60697046c2cac1627e9863170f2e6fe2cd`
- contract implementation: `8eb7d07e22159c32473b6e4142430da005912927`
- BAT: `61f385eda711845f14557af340a2b8d7b626c1a8`
- documentation: `d5765e8ca569049f14482e34e21a0bc150e842c0`

## 10. New-chat starter prompt

Paste the following into the next chat:

```text
repo: knitanr-a11y/xauusd-signal-lab

まず次の引き継ぎ文書を読んで、続きからお願いします。

docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_328_DONE_329_NEXT_PERSISTENT_ROUTER_PROSPECTIVE_RUNTIME_20260624.md

現在Stage328まで完了しています。
status:
GOLD_V3_328_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_CONTRACT_READY

decision:
WAIT_FOR_FIRST_POST_FREEZE_BALANCED_OR_PREMIUM_CANDIDATE

Stage328のcontractとbootstrapは初回実行で凍結済みです。
絶対に削除・再作成・更新・cutoff移動をしないでください。

次はStage329:
GOLD_V3_329_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_RUNTIME_AUDIT_ONLY

重要な絶対条件:
- GOLD V3はaudit-only
- GOLD V2 / 旧GOLD / DISC8 / Stage41を読まない・使わない・参照しない・fallbackにしない
- CSV最新行はclosedで、open/as-of扱いしない
- MT5 server time
- closed dataだけでentry判定
- pendingにas-of PnLを付けない
- state更新はsource candidateのresolution後だけ
- routerで除外したcandidateもresolution後にgroup historyを更新
- Stage328 frozen contract/bootstrapを変更しない
- Stage319 cutoff `decision_dt > 2026-06-23 13:55:00` を厳守
- policyは `RELATIVE_TRAILING_MEAN_R_N2` 固定
- laneは `BALANCED_OR_PREMIUM` 固定
- 2026データを選抜・再調整に使わない
- parity toleranceは1e-12のまま
- candidate poolを勝手に外さない
- Stage280 exact recoveryはBLOCKEDのまま
- Stage307 / Stage292 / Stage314 / Stage319を変更しない
- MT5 orders OFF / Discord OFF / partial close OFF
- automatic promotion禁止

Stage329では、frozen bootstrapを別のmutable runtime stateへ初回だけコピーし、以後はstateを永続化して、future-only source candidatesをappend-only・idempotentに監視してください。

GitHub mainへ本体、BAT、仕様書を直接コミットし、実行用BATを1行で示してください。
日本語で結果と変更理由を説明してください。
```
