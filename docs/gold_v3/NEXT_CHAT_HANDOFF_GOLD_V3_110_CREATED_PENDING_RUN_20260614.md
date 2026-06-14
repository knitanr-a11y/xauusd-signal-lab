# NEXT CHAT HANDOFF — GOLD V3 110 created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_110_AUDIT_MONITORING_DESIGN_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## Current context

109 completed READY:

```text
status: GOLD_V3_109_BASE_POLICY_SELECTION_REVIEW_PACKET_READY_AUDIT_ONLY
decision: BASE_POLICY_SELECTION_READY_FOR_STAGE110_AUDIT_MONITORING_DESIGN
selected_option: KEEP_107Q_BASE
selected_policy_key: 107Q_BASE_RESOLVED_PASS_THROUGH
health_gate_adopted: false
```

Selected base metrics:

```text
trades: 5571
wins: 3550
losses: 2019
win_rate: 0.6372285047567762
profit_factor: 3.129035220079588
sum_result_usd: 18065.748437500006
negative_month_count: 0
unique_trade_days: 100
max_day_trade_share: 0.05726081493448214
```

## What 110 does

110 designs audit-only virtual monitoring.

It reads:

```text
FX_OUTPUTS/gold_v3/109c/gold_v3_109_selected_base_policy_ledger.csv
FX_OUTPUTS/gold_v3/109c/gold_v3_109_summary.json
```

It writes:

```text
gold_v3_110_monitoring_thresholds.csv
gold_v3_110_historical_rolling_distribution.csv
gold_v3_110_monthly_monitoring_baseline.csv
gold_v3_110_regime_monitoring_baseline.csv
gold_v3_110_virtual_monitoring_runbook.md
```

Monitoring windows:

```text
rolling 20 resolved trades
rolling 50 resolved trades
rolling 100 resolved trades
```

Thresholds use historical distributions:

```text
watch: q25
caution: q10
stop-review: q05
```

All actions are audit review only.

## Important interpretation

`exit_dt` is not an entry condition. It is only used for resolved-only history:

```text
past_trade.exit_dt <= monitoring_time
```

## Files created

```text
docs/gold_v3/GOLD_V3_110_AUDIT_MONITORING_DESIGN_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_110_audit_monitoring_design.py
scripts/gold_v3_runtime/bat/run_gold_v3_110_audit_monitoring_design.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_110_CREATED_PENDING_RUN_20260614.md
```

## Run next

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_110_audit_monitoring_design.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/110c/paste_me.txt
```

Expected decision:

```text
AUDIT_MONITORING_DESIGN_READY_FOR_STAGE111_VIRTUAL_MONITOR_DRY_RUN
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
