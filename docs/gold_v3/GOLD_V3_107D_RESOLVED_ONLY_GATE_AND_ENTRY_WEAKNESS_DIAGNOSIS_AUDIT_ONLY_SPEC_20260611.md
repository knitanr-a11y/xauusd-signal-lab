# GOLD V3 Stage107D Spec — RESOLVED_ONLY_GATE_AND_ENTRY_WEAKNESS_DIAGNOSIS_AUDIT_ONLY

Created JST: `2026-06-11`

Repo: `knitanr-a11y/xauusd-signal-lab`

Stage:

```text
GOLD_V3_107D_RESOLVED_ONLY_GATE_AND_ENTRY_WEAKNESS_DIAGNOSIS_AUDIT_ONLY
```

## Purpose

Stage107D answers two questions raised by Stage107C:

1. Can the health-gate performance be recovered using only live-knowable, already-resolved outcomes?
2. If not, does the entry condition itself need to be changed, and where is the weakness concentrated?

This stage is audit-only. It does not change runtime signal conditions.

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

Stage107D reads Stage107 outputs only:

```text
FX_OUTPUTS/gold_v3/107c/gold_v3_107_long_short_proxy_ledger.csv
FX_OUTPUTS/gold_v3/107c/gold_v3_107_direction_assumption_summary.json
```

Optional reference only:

```text
FX_OUTPUTS/gold_v3/107cc/gold_v3_107c_gate_mode_summary.csv
```

Stage107D does not rebuild candidates and does not scan MQL5/Files broadly.

## Method

Stage107D performs a resolved-only health gate parameter search. All candidate histories must be based only on rows whose `exit_dt <= current entry_dt`.

Search dimensions:

```text
window: 10, 15, 20, 30
min_history: 5, 8, 10, 15
pf_threshold: 1.00, 1.10, 1.25, 1.50
loss_streak_lt: 1, 2, 3
proxy_side: LONG, SHORT
population: all_rows, normal_only, hv_named_only, true_high_vol_only, non_true_high_vol_only
```

Primary comparison metrics:

```text
trades
win_rate
profit_factor
sum_result_usd
recent_2026_03_plus_profit_factor
recent_2026_05_06_profit_factor
negative_month_count
score
```

The score should prefer high PF, positive sum, enough trades, and fewer negative months. It is an audit ranking only, not a trading approval.

## Entry weakness diagnosis

Stage107D must also summarize raw entry weakness by:

```text
proxy_side
hv_sibling
is_high_vol
source_rank
profile_id
jst_hour
jst_weekday
entry_month
```

The goal is to identify whether poor live-rehydrated performance is mostly a gate parameter problem or an entry-condition/regime problem.

## Outputs

Implementation paths:

```text
docs/gold_v3/GOLD_V3_107D_RESOLVED_ONLY_GATE_AND_ENTRY_WEAKNESS_DIAGNOSIS_AUDIT_ONLY_SPEC_20260611.md
scripts/gold_v3_runtime/gold_v3_107d_resolved_only_gate_and_entry_weakness_diagnosis_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107d_resolved_only_gate_and_entry_weakness_diagnosis.bat
```

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107dc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107dc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107d_resolved_only_grid_summary.csv
gold_v3_107d_top_resolved_only_configs.csv
gold_v3_107d_top_config_selected_trade_ledger.csv
gold_v3_107d_raw_entry_weakness_by_month.csv
gold_v3_107d_raw_entry_weakness_by_segment.csv
gold_v3_107d_blocker_matrix.csv
gold_v3_107d_validation_matrix.csv
gold_v3_107d_summary.json
GOLD_V3_107D_RESOLVED_ONLY_GATE_AND_ENTRY_WEAKNESS_DIAGNOSIS_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107D_RESOLVED_ONLY_GATE_AND_ENTRY_WEAKNESS_DIAGNOSIS_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107D_RESOLVED_ONLY_GATE_AND_ENTRY_WEAKNESS_DIAGNOSIS_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```

Even when BLOCKED, Stage107D must write `FX_OUTPUTS/gold_v3/107dc/paste_me.txt`.

## Non-goals

Stage107D does not:

- approve live trading;
- change signal conditions;
- change direction;
- repair HV sibling polarity;
- change candidate pool;
- enable live evaluator or final signal.
