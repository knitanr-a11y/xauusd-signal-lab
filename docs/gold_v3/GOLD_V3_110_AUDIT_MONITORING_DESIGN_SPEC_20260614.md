# GOLD V3 Stage110 Spec — AUDIT_MONITORING_DESIGN

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_110_AUDIT_MONITORING_DESIGN
```

## Why this stage exists

Stage109 selected the review candidate:

```text
selected_option: KEEP_107Q_BASE
selected_policy_key: 107Q_BASE_RESOLVED_PASS_THROUGH
health_gate_adopted: false
```

Stage109 metrics:

```text
trades: 5571
win_rate: 63.7229%
profit_factor: 3.1290
sum_result_usd: 18065.7484
negative_month_count: 0
unique_trade_days: 100
max_day_trade_share: 5.7261%
```

Stage110 designs audit-only monitoring for this selected policy. It does not create a live signal.

## Purpose

Stage110 creates an audit-only monitoring design for the selected base policy.

It must:

1. Read the selected Stage109 ledger.
2. Confirm resolved-only columns remain present.
3. Compute historical rolling-monitor distributions.
4. Propose virtual monitoring thresholds.
5. Define watch, caution, and stop-review levels.
6. Keep all live/MT5/Discord/final signal paths disabled.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/109c/gold_v3_109_selected_base_policy_ledger.csv
FX_OUTPUTS/gold_v3/109c/gold_v3_109_summary.json
```

Optional:

```text
FX_OUTPUTS/gold_v3/109c/gold_v3_109_base_policy_monthly_metrics.csv
FX_OUTPUTS/gold_v3/109c/gold_v3_109_base_policy_regime_metrics.csv
```

## Monitoring design scope

Stage110 can define monitoring checks such as:

```text
rolling 20 resolved trades WR/PF
rolling 50 resolved trades WR/PF
rolling 100 resolved trades WR/PF
monthly WR/PF/sum checks
daily concentration checks
candidate/regime degradation checks
```

Monitoring must use only resolved outcomes:

```text
exit_dt <= current monitoring time
```

`exit_dt` is not an entry feature.

## Outputs

```text
FX_OUTPUTS/gold_v3/110c/gold_v3_110_monitoring_thresholds.csv
FX_OUTPUTS/gold_v3/110c/gold_v3_110_historical_rolling_distribution.csv
FX_OUTPUTS/gold_v3/110c/gold_v3_110_monthly_monitoring_baseline.csv
FX_OUTPUTS/gold_v3/110c/gold_v3_110_regime_monitoring_baseline.csv
FX_OUTPUTS/gold_v3/110c/gold_v3_110_virtual_monitoring_runbook.md
FX_OUTPUTS/gold_v3/110c/gold_v3_110_quality_gate_matrix.csv
FX_OUTPUTS/gold_v3/110c/gold_v3_110_blocker_matrix.csv
FX_OUTPUTS/gold_v3/110c/gold_v3_110_validation_matrix.csv
FX_OUTPUTS/gold_v3/110c/gold_v3_110_summary.json
FX_OUTPUTS/gold_v3/110c/GOLD_V3_110_AUDIT_MONITORING_DESIGN_REPORT.md
FX_OUTPUTS/gold_v3/110c/paste_me.txt
```

## Decision

Allowed decisions:

```text
AUDIT_MONITORING_DESIGN_READY_FOR_STAGE111_VIRTUAL_MONITOR_DRY_RUN
AUDIT_MONITORING_DESIGN_BLOCKED_INPUT_INCOMPLETE
```

## What this stage must not approve

Stage110 must not approve:

- live signal
- MT5 execution
- Discord alerts
- AI API
- live hook
- final signal
- candidate pool removal

## Guardrails

GOLD V3 remains audit-only.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime, Stage69 runtime, live evaluator, live hook, final signal, Discord, MT5, or AI API.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 feature-only snapshot as a trading source.
