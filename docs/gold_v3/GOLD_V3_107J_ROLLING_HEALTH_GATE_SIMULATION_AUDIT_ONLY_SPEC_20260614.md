# GOLD V3 Stage107J Spec — ROLLING_HEALTH_GATE_SIMULATION_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107J_ROLLING_HEALTH_GATE_SIMULATION_AUDIT_ONLY
```

## Purpose

Stage107I2 exactly replayed the Stage107H score gate and found a practical candidate:

```text
replayed_trades: 63
replayed_win_rate: 82.54%
replayed_profit_factor: 6.78
replayed_business_day_trade_rate: 3.5
unique_trade_days: 5
max_day_trade_share: 26.98%
exact_replay_ready: true
```

Stage107J simulates rolling health gates on this exact-replayed candidate using only resolved history available before each new entry.

## Guardrails

GOLD V3 remains audit-only.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 as trading sources.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime behavior, Stage69 runtime behavior, live evaluator, final signal, Discord, MT5 execution, or AI API.

CSV contract:

```text
open/in-progress candles are not written to CSV
CSV latest row is contractually closed
open/as-of treatment is forbidden
```

Pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```

## Resolved-only rule

For every candidate entry at `entry_dt`, health history must only include prior outcomes whose:

```text
exit_dt <= current entry_dt
```

No current trade result or unresolved future horizon may be added to history before its exit time.

## Inputs

```text
FX_OUTPUTS/gold_v3/107i2c/gold_v3_107i2_exact_replay_candidates.csv
FX_OUTPUTS/gold_v3/107i2c/gold_v3_107i2_all_replayed_ledgers.csv
```

## Health modes

Two modes are evaluated:

```text
shadow_history
```

Uses all exact-score-gate virtual candidate outcomes once resolved. This is appropriate for audit-only virtual monitoring.

```text
traded_only
```

Uses only previously gate-passed trades as history. This is more conservative for live execution.

## Gate grid

Examples:

```text
min_history: 3, 5, 8, 10
min_wr: 0.50, 0.55, 0.60, 0.65
min_pf: 1.00, 1.30, 1.50, 2.00
lookback_resolved: all, 20, 50
```

## Pass gates

Primary:

```text
WR >= 65%
PF >= 1.50
trades >= 30
unique_trade_days >= 4
max_day_trade_share <= 0.45
```

## Outputs

```text
FX_OUTPUTS/gold_v3/107jc/
```

Mandatory paste file:

```text
FX_OUTPUTS/gold_v3/107jc/paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107J_ROLLING_HEALTH_GATE_SIMULATION_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107J_ROLLING_HEALTH_GATE_SIMULATION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
