# NEXT CHAT HANDOFF — GOLD V3 107Q created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_107Q_STABLE_FILTER_FAMILY_REPLAY_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## Current context

107P completed and showed that shortening rolling lookback did not fix the adaptive trim:

```text
status: GOLD_V3_107P_ROLLING_LOOKBACK_PARAMETER_SWEEP_READY_AUDIT_ONLY
decision: ROLLING_LOOKBACK_SWEEP_NOT_CONFIRMED_NEED_RULE_FAMILY_CHANGE
best_combo_key: L5_T5
best_rolling_wr: 0.5952205882352941
best_rolling_pf: 2.4803978513892067
best_rolling_retention: 0.6606752489676949
best_rolling_wr_gain: -0.005580966294703504
best_min_regime_wr: 0.5878226008519168
best_primary_gate: false
best_review_gate: false
```

This means the issue is probably not simply lookback length. The free rolling feature-selection method is unstable and often removes target-window winners.

## What 107Q does

107Q changes the rule family.

Instead of selecting any feature freely in each rolling window, it:

1. Reads the 107M loss-trim frontier.
2. Extracts top unique stable families:

```text
family = feature + op + side_scope
```

3. For each family and each rolling combo, only selects the threshold from the train window.
4. Applies that threshold to the target window.
5. Ranks stable families by WR/PF gain, retention, min_regime_wr, and negative month count.

Default:

```text
family_top_n: 30
lookback_active_days: 20,10,5
target_active_days: 5,3,1
min_train_rows: 150
min_removed: 10
min_retention: 65%
```

The 107M best family is always included if missing:

```text
feature: m15_dist_atr
op: >=
side_scope: ALL
```

## Files created

```text
docs/gold_v3/GOLD_V3_107Q_STABLE_FILTER_FAMILY_REPLAY_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_107q_stable_filter_family_replay_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107q_stable_filter_family_replay.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_107Q_CREATED_PENDING_RUN_20260614.md
```

## Run next

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_107q_stable_filter_family_replay.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/107qc/paste_me.txt
```

## Important limitation

The 107L ledger still lacks `exit_dt`. Therefore 107Q is still a proxy audit, not strict resolved-only live replay.

Even if 107Q passes, `live_ready` remains false until a resolved ledger proves:

```text
exit_dt <= current entry_dt
```

## Hard guardrails

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

Pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```
