# GOLD V3 119 JUNE CURRENT PERIOD BACKTEST AUDIT REPORT

Created JST: `2026-06-15`

## Status

```text
GOLD_V3_119_JUNE_CURRENT_PERIOD_BACKTEST_AUDIT_ONLY
```

## Important execution note

The local `FX_OUTPUTS` data files are not stored in GitHub, so this chat cannot execute the local CSV/ledger run directly against the user's PC files.

A rerunnable audit-only script and BAT were added so the same June current-period aggregation can be run locally.

```text
scripts/gold_v3_runtime/gold_v3_119_june_current_period_backtest_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_119_june_current_period_backtest_audit.bat
```

## Current known June period from existing Stage117 outputs

Available June period in current upstream data:

```text
2026-06-01 <= entry_dt < 2026-07-01
max known June upstream entry_dt: 2026-06-05 15:15:00
```

Current selected F002 policy:

```text
109c selected ledger June rows: 0
107Q/117J best family June rows: 0
```

107L upstream June rows before F002 exclusion:

```text
trades: 8
wins: 4
losses: 4
WR: 50.00%
PF: 2.000
sum_result_usd: +37.50
```

F002 exclusion review:

```text
F002 threshold: score <= 1715.701299
removed_rows: 8
kept_rows: 0
```

Therefore, under the current selected policy / F002 exclusion maintained:

```text
June selected-policy trades: 0
June selected-policy WR: 0.00%
June selected-policy PF: 0.000
June selected-policy sum_result_usd: +0.00
```

Review-only restore-all-8 comparison:

```text
review_only_trades_added: 8
review_only_WR: 50.00%
review_only_PF: 2.000
review_only_sum_result_usd: +37.50
```

This remains review-only and is not adopted into live/demo policy.

## Stage119 output buckets

The script outputs these separated buckets:

```text
raw_107l_june
  107L upstream June rows before F002 selected exclusion

dedup_107l_june
  deduplicated 107L upstream June rows

health_gate_selected_109c_june
  current selected policy after F002 exclusion

shadow_117j_best_june
  shadow 107Q best family after F002 exclusion

f002_removed_june_review_only
  June rows removed by F002; review-only

f002_kept_june
  June rows kept by F002

restore_all_8_review_only
  selected policy plus all removed June rows; review-only

resolved_only_live_repro_selected_june
  resolved-only view of current selected policy
```

## Expected local outputs

```text
FX_OUTPUTS/gold_v3/119/gold_v3_119_summary.json
FX_OUTPUTS/gold_v3/119/gold_v3_119_decision.csv
FX_OUTPUTS/gold_v3/119/gold_v3_119_june_current_period_backtest_comparison.csv
FX_OUTPUTS/gold_v3/119/gold_v3_119_june_direction_split.csv
FX_OUTPUTS/gold_v3/119/gold_v3_119_raw_107l_june_rows.csv
FX_OUTPUTS/gold_v3/119/gold_v3_119_selected_109c_june_rows.csv
FX_OUTPUTS/gold_v3/119/gold_v3_119_f002_removed_june_review_rows.csv
FX_OUTPUTS/gold_v3/119/paste_me.txt
```

## Safety flags

```text
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
candidate_pool_removed: false
f002_exclusion_bypassed: false
june_restore_auto_adopted: false
review_only: true
```

## Local run command

```bat
scripts\gold_v3_runtime\bat\run_gold_v3_119_june_current_period_backtest_audit.bat
```
