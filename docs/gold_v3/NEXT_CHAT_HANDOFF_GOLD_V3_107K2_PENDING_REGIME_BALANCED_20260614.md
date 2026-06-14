# NEXT CHAT HANDOFF — GOLD V3 107K2 pending regime-balanced audit

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_107K2_DIRECT_REGIME_BALANCED_ADAPTIVE_SCORE_PENDING_AUDIT_ONLY
```

The user will attach the next result in the new chat:

```text
FX_OUTPUTS/gold_v3/107k2c/paste_me.txt
```

## High-level objective

Do not optimize for one narrow month.

The user clarified the core objective:

```text
2025 and 2026 are materially different markets.
2026 has higher volatility.
The system must flexibly handle both regimes and preserve performance across them.
```

Therefore, the next decision must judge whether the method works across both 2025 and 2026 high-volatility regimes.

## Global guardrails

GOLD V3 remains audit-only.

Do not read/use/reference/fallback to:

- GOLD V2
- old GOLD
- DISC8
- Stage41 feature-only snapshot as a trading source

Do not mutate:

- source CSVs
- CSV contract
- candidate pool
- Stage45 runtime
- Stage69 runtime
- live evaluator
- live hook
- final signal
- Discord
- MT5 execution
- AI API

CSV contract:

```text
open/in-progress candles are not written to CSV
CSV latest row is contractually closed
csv_open_bar_exclusion_required=false
```

Health / rolling gate rule:

```text
Only resolved outcomes with exit_dt <= current entry_dt may enter history.
```

Pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```

## What was done in this chat

### Stage107GY — light non-calendar subfilter search

Output directory:

```text
FX_OUTPUTS/gold_v3/107gyc
```

Result:

```text
status: GOLD_V3_107GY_LIGHT_NON_CALENDAR_SUBFILTER_SEARCH_READY_AUDIT_ONLY
primary_65_gate_count: 0
volume_65_gate_count: 0
review_62_gate_count: 0
best_wr: 61.46%
best_pf: 2.397
best_trades: 96
best_density: 3.2/day
decision: NO_65_NEED_DEEPER_FEATURES
```

Interpretation:

- Better than prior baseline.
- Did not reach 65%.
- Suggested deeper feature search.

### Stage107GZ — two-condition feature pair search

Output directory:

```text
FX_OUTPUTS/gold_v3/107gzc
```

Result:

```text
status: GOLD_V3_107GZ_DEEPER_FEATURE_PAIR_SEARCH_READY_AUDIT_ONLY
primary_65_gate_count: 0
review_63_gate_count: 0
small_65_gate_count: 0
best_wr: 60.0%
best_pf: 2.45
best_trades: 15
best_density: 0.75/day
decision: NO_65_PAIR_FILTER_NEED_NEW_VECTOR_OR_MODEL_FEATURES
```

Interpretation:

- Hard AND filtering worsened coverage and did not improve WR.
- Do not continue this direction blindly.

### Stage107H — train-only feature score gate

Output directory:

```text
FX_OUTPUTS/gold_v3/107hc
```

Result:

```text
status: GOLD_V3_107H_TRAIN_ONLY_FEATURE_SCORE_GATE_READY_AUDIT_ONLY
primary_65_gate_count: 8
review_63_gate_count: 6
small_65_gate_count: 16
summary best: 22 trades / 100% WR / 1-day concentrated
practical row: 63 trades / 82.54% WR / PF 6.78 / 3.5/day
```

Interpretation:

- Strong candidate found.
- Summary-best was unsafe because it was concentrated in one day.
- Practical 63-trade row required exact replay.

### Stage107I — first rehydration attempt

Output directory:

```text
FX_OUTPUTS/gold_v3/107ic
```

Result:

```text
status: GOLD_V3_107I_RESOLVED_ONLY_REHYDRATION_AND_CONCENTRATION_READY_AUDIT_ONLY
rehydration_ready_count: 0
primary_65_rehydrated_count: 0
source_oos_trades 63 became rehydrated_trades 828
metric_match_trades=false
metric_match_wr=false
```

Interpretation:

- Do not treat this as strategy failure.
- It revealed the replay logic was wrong.
- Likely cause: persisted feature-bin rows were reused by split/tier/base_top_n and duplicated.

### Stage107I2 — exact score gate replay

Output directory:

```text
FX_OUTPUTS/gold_v3/107i2c
```

Result:

```text
status: GOLD_V3_107I2_EXACT_SCORE_GATE_REPLAY_READY_AUDIT_ONLY
exact_replay_ready_count: 6
primary_65_replayed_count: 8
metric_match_count: 8
best_trades: 63
best_wr: 82.54%
best_pf: 6.78
best_density: 3.5/day
best_unique_trade_days: 5
best_max_day_trade_share: 26.98%
decision: EXACT_REPLAY_PRIMARY_65_READY_FOR_HEALTH_GATE_AUDIT
```

Interpretation:

- 107H practical row was real under exact replay.
- But it is still heavily 2026 May / May-June oriented.
- Do not finish based only on this.

### Stage107J — rolling health gate attempt

Output directory:

```text
FX_OUTPUTS/gold_v3/107jc
```

Result:

```text
status: GOLD_V3_107J_ROLLING_HEALTH_GATE_SIMULATION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
blocker: missing_exit_dt_or_replay_rows
reason: resolved-only health gate requires exit_dt
```

Interpretation:

- This was not a performance failure.
- It is blocked because the replay ledger lacks the resolved exit timestamps required for live-faithful health-gate history.
- Do not continue rolling health gate until exit_dt is available or reconstructed from valid resolved ledgers without future leakage.

### Stage107K — first regime-balanced attempt

Output directory:

```text
FX_OUTPUTS/gold_v3/107kc
```

Result:

```text
status: GOLD_V3_107K_REGIME_BALANCED_ADAPTIVE_SCORE_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
blocker: no_regime_frontier
```

Interpretation:

- This was not a strategy failure.
- It was an evaluation design bug: the script searched for new split names such as `REGIME_2025_H2` inside an older config file that did not contain them.

### Stage107K2 — direct regime-balanced adaptive score audit

Files created:

```text
docs/gold_v3/GOLD_V3_107K2_DIRECT_REGIME_BALANCED_ADAPTIVE_SCORE_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_107k2_direct_regime_balanced_adaptive_score_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107k2_direct_regime_balanced_adaptive_score.bat
```

Output expected:

```text
FX_OUTPUTS/gold_v3/107k2c/paste_me.txt
```

107K2 fixes 107K by directly projecting the Stage107GU candidate key bank into regime windows:

```text
REGIME_2025_H2
train: 2025-01-01 to 2025-07-01
test:  2025-07-01 to 2026-01-01

REGIME_2026_Q1Q2
train: 2025-01-01 to 2026-01-01
test:  2026-01-01 to 2026-05-01

REGIME_2026_HIGHVOL_MAYJUN
train: 2025-01-01 to 2026-05-01
test:  2026-05-01 to 2027-01-01
```

## Next chat action

1. Read this handoff.
2. Read the user's attached `107k2c/paste_me.txt`.
3. If `107K2` is READY:
   - summarize per-regime results.
   - focus on `all_regime_pass_65_count`, `all_regime_pass_60_count`, `best_min_wr`, `best_min_pf`, `best_min_trades`, and `best_policy_regime_rows`.
4. If `107K2` is BLOCKED:
   - identify blocker.
   - do not call it strategy failure unless regime frontier was created and metrics actually failed.
5. If a balanced policy exists:
   - next stage should be `107L_REGIME_REHYDRATION_AND_HEALTH_GATE_AUDIT_ONLY`.
6. If no balanced policy exists:
   - next stage should be `107L_ADAPTIVE_BASE_CANDIDATE_GENERATION_AUDIT_ONLY`.

## Completion roadmap from here

### Path A: 107K2 finds balanced policy

1. `107L_REGIME_REHYDRATION_AND_HEALTH_GATE_AUDIT_ONLY`
   - exact replay per regime.
   - verify no metric mismatch.
   - reconstruct or source `exit_dt` for resolved-only health gate.
2. `107M_MULTI_REGIME_ROLLING_HEALTH_GATE_AUDIT_ONLY`
   - run `exit_dt <= current entry_dt` gates.
   - compare `shadow_history` and `traded_only` modes.
3. `107N_DEPLOYABILITY_REVIEW_PACKET_AUDIT_ONLY`
   - summarize raw / score-gated / health-gated / per-regime metrics.
4. `107O_HUMAN_DECISION_PACKET_AUDIT_ONLY`
   - user decides whether to keep tuning, request more audit, or prepare audit-only virtual monitor.
5. Only after explicit human approval: live/Discord/MT5 decisions.

### Path B: 107K2 finds no balanced policy

1. `107L_ADAPTIVE_BASE_CANDIDATE_GENERATION_AUDIT_ONLY`
   - do not simply filter May winners.
   - create separate candidate families for 2025 regime and 2026 high-vol regime.
   - design a live-knowable regime selector based on ATR/volatility/trend state.
2. `107M_REGIME_SWITCHING_POLICY_AUDIT_ONLY`
   - select 2025-family or 2026-family by live-known regime state.
3. `107N_REGIME_SWITCHING_REHYDRATION_AUDIT_ONLY`
   - exact replay and resolved-only history.
4. `107O_DEPLOYABILITY_REVIEW_PACKET_AUDIT_ONLY`.

## Important warning for next assistant

Do not chase the 2026 May result alone.

Any answer that says the system is close to finished based only on `2026-05-06 to 2026-05-29` is wrong.

The correct acceptance lens is:

```text
Can the same live-knowable adaptive framework preserve acceptable performance across both 2025 and 2026 high-volatility regimes?
```
