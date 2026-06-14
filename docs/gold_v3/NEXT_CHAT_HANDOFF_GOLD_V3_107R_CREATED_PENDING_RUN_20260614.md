# NEXT CHAT HANDOFF — GOLD V3 107R created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_107R_RESOLVED_EXIT_DT_REHYDRATION_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## Current context

107Q completed with a strong primary PASS:

```text
status: GOLD_V3_107Q_STABLE_FILTER_FAMILY_REPLAY_READY_AUDIT_ONLY
decision: STABLE_FILTER_FAMILY_PRIMARY_READY_FOR_RESOLVED_EXIT_DT_REPLAY
best_combo_key: F002_L20_T5
best_feature: score
best_op: <=
best_side_scope: ALL
best_lookback_active_days: 20
best_target_active_days: 5
best_family_wr: 0.6372285047567762
best_family_pf: 3.129035220079588
best_family_retention: 0.7297615928739848
best_family_wr_gain: 0.033875085841397645
best_min_regime_wr: 0.628641975308642
best_primary_gate: true
best_review_gate: true
```

This is the strongest post-107K2 result so far. Stable family replay succeeded where free rolling feature selection failed.

## Remaining blocker

107Q is still proxy-only:

```text
live_ready: false
resolved_only_strict: false
posthoc_seed_family_not_final: true
```

Strict resolved-only replay requires:

```text
exit_dt <= current entry_dt
```

The next priority is therefore not more filter search. It is `exit_dt` rehydration.

## What 107R does

107R searches local audit outputs under:

```text
FX_OUTPUTS/gold_v3
```

for CSV files with an exact column:

```text
exit_dt
```

It then attempts safe joins into:

```text
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_best_family_trade_ledger.csv
```

Join priority:

```text
global_candidate_key
entry_dt + global_candidate_key
entry_dt + side + candidate_key + profile_id
entry_dt + side + family + condition + profile_id
entry_dt + side + result_usd
```

A join is accepted only if:

```text
coverage == 100%
non_null_exit_dt == selected_rows
exit_dt >= entry_dt for all selected rows
```

## Files created

```text
docs/gold_v3/GOLD_V3_107R_RESOLVED_EXIT_DT_REHYDRATION_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_107r_resolved_exit_dt_rehydration_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107r_resolved_exit_dt_rehydration.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_107R_CREATED_PENDING_RUN_20260614.md
```

## Run next

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_107r_resolved_exit_dt_rehydration.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/107rc/paste_me.txt
```

## Expected outcomes

If 107R finds and joins full `exit_dt` coverage:

```text
RESOLVED_EXIT_DT_REHYDRATION_READY_FOR_107S_HEALTH_GATE_REPLAY
```

If no exact `exit_dt` source exists:

```text
RESOLVED_EXIT_DT_REHYDRATION_BLOCKED_EXIT_DT_SOURCE_NOT_FOUND
```

If an exit source exists but does not join cleanly:

```text
RESOLVED_EXIT_DT_REHYDRATION_BLOCKED_PARTIAL_OR_AMBIGUOUS_JOIN
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
