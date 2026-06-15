# GOLD V3 120 JUNE 01-15 BACKTEST CHAIN AUDIT REPORT

Created JST: `2026-06-15`

## Why Stage120 was added

Stage119 initially summarized the currently known Stage117 output, but that output only had upstream 107L June coverage through `2026-06-05 15:15:00`.

The user requested the June test through June 15. Stage120 therefore adds a local audit chain that requires the upstream 107L input to reach at least `2026-06-15` before accepting the June 01-15 result.

## Added / updated artifacts

```text
updated: scripts/gold_v3_runtime/gold_v3_119_june_current_period_backtest_audit.py
added:   scripts/gold_v3_runtime/bat/run_gold_v3_120_june_01_15_backtest_chain_audit.bat
```

## Local run command

```bat
scripts\gold_v3_runtime\bat\run_gold_v3_120_june_01_15_backtest_chain_audit.bat
```

## What the BAT does

```text
[1/6] Working directory set
[2/6] Shadow rerun Stage117J from current 107L and 107M inputs
[3/6] Rebuild Stage117L June F002 removed detail
[4/6] Rebuild Stage117M review-only restore comparison
[5/6] Run Stage119 period audit 2026-06-01 through 2026-06-15
[6/6] Output location
```

Stage119 is now called as:

```bat
py -3 scripts\gold_v3_runtime\gold_v3_119_june_current_period_backtest_audit.py --start 2026-06-01 --end-exclusive 2026-06-16 --require-min-input-max-entry-dt 2026-06-15
```

## Coverage gate

If local `FX_OUTPUTS/gold_v3/107lc/gold_v3_107l_rehydrated_best_policy_ledger.csv` still ends on `2026-06-05`, Stage119 will block with:

```text
upstream_107l_does_not_reach_required_target
```

That is intentional. It prevents reporting a June 01-15 backtest while the actual candidate input still only reaches June 5.

If the local 107L ledger has been regenerated and reaches June 15, Stage120 will produce the June 01-15 report.

## Outputs

```text
FX_OUTPUTS/gold_v3/117j/paste_me.txt
FX_OUTPUTS/gold_v3/117l/paste_me.txt
FX_OUTPUTS/gold_v3/117m/paste_me.txt
FX_OUTPUTS/gold_v3/119/paste_me.txt
FX_OUTPUTS/gold_v3/119/gold_v3_119_summary.json
FX_OUTPUTS/gold_v3/119/gold_v3_119_period_backtest_comparison.csv
FX_OUTPUTS/gold_v3/119/gold_v3_119_period_direction_split.csv
```

## Safety flags

```text
audit_only: true
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
candidate_pool_removed: false
f002_exclusion_bypassed: false
period_restore_auto_adopted: false
```

## Interpretation

A valid June 01-15 result requires:

```text
observed_107l_max_entry_dt >= 2026-06-15
status: GOLD_V3_119_JUNE_CURRENT_PERIOD_BACKTEST_AUDIT_ONLY_READY
```

If this fails, the correct next action is not to treat 0 trades as a true June 01-15 result. The correct next action is to regenerate the upstream 107L source chain audit-only from current local inputs, then rerun Stage120.
