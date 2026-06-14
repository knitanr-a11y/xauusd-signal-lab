# NEXT CHAT HANDOFF — GOLD V3 107L created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_107L_REGIME_REHYDRATION_AND_HEALTH_GATE_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## What was judged from 107K2

The attached Stage107K2 generated frontier was valid even though the 107K2 script crashed at the final summary writer.

The crash was a column prefix bug:

```text
AttributeError: 'DataFrame' object has no attribute 'unique_trade_days'
expected generated column: oos_unique_trade_days
```

Judgment from `gold_v3_107k2_regime_frontier.csv`:

```text
regime_frontier_rows: 252
policy_count: 84
all_regime_pass_65_count: 0
all_regime_pass_60_count: 12
decision: REGIME_BALANCED_60_READY_FOR_REVIEW
best_policy_key: density_safe||100||Q0.6
best_min_wr: 0.601742696053306
best_min_pf: 2.5352617898638443
best_min_trades: 146
best_sum_trades: 8565
```

Best policy per-regime rows:

```text
REGIME_2025_H2: 5853 trades, WR 60.17%, PF 2.535, actual OOS 2025-07-07 to 2025-12-31
REGIME_2026_Q1Q2: 2566 trades, WR 60.21%, PF 2.556, actual OOS 2026-01-05 to 2026-04-14
REGIME_2026_HIGHVOL_MAYJUN: 146 trades, WR 65.07%, PF 2.956, actual OOS 2026-05-06 to 2026-06-05
```

Important interpretation:

- This is not a strict 65 result.
- It is a balanced 60 result across the three regime rows.
- It is not live-ready.
- 2026 high-vol still has short actual data coverage.
- Health gate must not proceed unless `exit_dt` exists.

## Files created/updated

Created:

```text
docs/gold_v3/GOLD_V3_107K2_RESULT_REVIEW_FROM_FRONTIER_20260614.md
docs/gold_v3/GOLD_V3_107L_REGIME_REHYDRATION_AND_HEALTH_GATE_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_107l_regime_rehydration_and_health_gate_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107l_regime_rehydration_and_health_gate.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_107L_CREATED_PENDING_RUN_20260614.md
```

Updated:

```text
scripts/gold_v3_runtime/gold_v3_107k2_direct_regime_balanced_adaptive_score_audit.py
```

The 107K2 update only fixes audit-only summary aggregation column names. It does not change source CSVs, candidate pool, Stage45/Stage69 runtime, live evaluator, live hook, final signal, Discord, MT5, or AI API.

## Next action

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_107l_regime_rehydration_and_health_gate.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/107lc/paste_me.txt
```

## Expected outcome

Because the attached 107K2 all-regime ledger has no `exit_dt` column, the likely result is:

```text
REGIME_REHYDRATION_READY_HEALTH_GATE_BLOCKED_EXIT_DT_REQUIRED
```

That is not a strategy failure. It means the balanced policy exists, but rolling health gate cannot be live-faithfully simulated until a resolved-only ledger with `exit_dt` is available.

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

Health / rolling gate rule:

```text
Only resolved outcomes with exit_dt <= current entry_dt may enter history.
```

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
