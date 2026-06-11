# GOLD V3 Stage107C Spec — HEALTH_GATE_LIVE_REHYDRATION_AUDIT_ONLY

Created JST: `2026-06-11`

Repo: `knitanr-a11y/xauusd-signal-lab`

Stage:

```text
GOLD_V3_107C_HEALTH_GATE_LIVE_REHYDRATION_AUDIT_ONLY
```

## Purpose

Stage107C audits whether the Stage45/107B strict rolling health gate can be reproduced from information that would be known at live decision time.

The immediate question is:

```text
If strict rolling health gate plus HV siblings showed about 65% win rate, was that gate using only already-resolved prior outcomes, or did it benefit from updating candidate history at entry time before the future exit was knowable?
```

This stage is audit-only and does not approve live trading.

## Guardrails

GOLD V3 remains audit-only.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 as a trading source.

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

## Inputs

Stage107C reads Stage107 outputs only:

```text
FX_OUTPUTS/gold_v3/107c/gold_v3_107_long_short_proxy_ledger.csv
FX_OUTPUTS/gold_v3/107c/gold_v3_107_direction_assumption_summary.json
```

Primary input is `gold_v3_107_long_short_proxy_ledger.csv`.

Stage107C does not rebuild candidates and does not scan MQL5/Files broadly.

## Health gate modes

Stage107C must compare two gate modes for LONG and SHORT separately:

### 1. entry_update_stage45_style

This mirrors Stage45/107B style:

- process groups by `entry_dt`;
- select the first allowed row by `priority`, `candidate_label`;
- after the entry group, append every candidate row's `result_usd` to its candidate history;
- this may be optimistic for live if another entry occurs before those virtual outcomes are actually resolved.

### 2. exit_known_live_rehydrated

This live-rehydrated proxy mode:

- process groups by `entry_dt`;
- before each decision time, append only candidate outcomes whose `exit_dt <= current entry_dt`;
- pending outcomes are not available yet;
- selection uses only history that would have been knowable at decision time;
- it still assumes a virtual monitoring ledger exists for every candidate row, because Stage45 health gate history is candidate-level, not only selected-trade-level.

## Surfaces

Audit at least:

```text
strict_health_gate_no_hv
strict_health_gate_plus_hv_siblings
```

For each:

```text
proxy_side = LONG
proxy_side = SHORT
mode = entry_update_stage45_style
mode = exit_known_live_rehydrated
```

Default health gate parameters:

```text
window = 30
min_history = 20
pf_threshold = 1.10
loss_streak_lt = 3
```

## Required outputs

Implementation paths:

```text
docs/gold_v3/GOLD_V3_107C_HEALTH_GATE_LIVE_REHYDRATION_AUDIT_ONLY_SPEC_20260611.md
scripts/gold_v3_runtime/gold_v3_107c_health_gate_live_rehydration_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107c_health_gate_live_rehydration.bat
```

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107cc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107cc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107c_gate_mode_summary.csv
gold_v3_107c_gate_mode_monthly_summary.csv
gold_v3_107c_gate_mode_diff_summary.csv
gold_v3_107c_selected_trade_ledger.csv
gold_v3_107c_pending_lag_summary.csv
gold_v3_107c_blocker_matrix.csv
gold_v3_107c_validation_matrix.csv
gold_v3_107c_health_gate_live_rehydration_summary.json
GOLD_V3_107C_HEALTH_GATE_LIVE_REHYDRATION_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107C_HEALTH_GATE_LIVE_REHYDRATION_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107C_HEALTH_GATE_LIVE_REHYDRATION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```

Even when BLOCKED, Stage107C must write `FX_OUTPUTS/gold_v3/107cc/paste_me.txt`.

## Non-goals

Stage107C does not:

- approve live trading;
- change Stage45/69;
- change candidate pool;
- change direction;
- repair HV sibling polarity;
- resolve JST vs MT5/CSV time basis;
- enable live evaluator or final signal.
