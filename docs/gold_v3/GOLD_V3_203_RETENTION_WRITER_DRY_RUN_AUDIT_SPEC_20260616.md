# GOLD V3 Stage203 Retention Writer Dry-Run Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage203 creates dry-run samples for the practical retention model.

It separates short-retention notification history from long-retention trade history.

## User decision reflected

Old notification history is rarely useful after about one month.

Trade history must be retained long-term because it is needed later to review:

- why losses happened
- win rate
- PF
- trade count
- weak candidates
- weak time ranges
- PRIMARY versus SECONDARY_AUDIT_CANDIDATE behavior

## Proposed retention files

### Short retention

`notification_events_rolling_30d.csv`

- signal notification event history
- intended retention: about 30 days
- NO_SIGNAL is not appended as a notification event

### Long retention

`trade_signal_ledger.csv`

- append each signal event
- used for later signal frequency and trade count review

`trade_result_ledger.csv`

- append or update resolved results after exit
- used for win rate, PF, loss reason review, and monthly reports

`trade_history_monthly_summary.csv`

- monthly aggregate derived from trade result ledger

### Health and debug

`latest_state.json`

- overwritten each evaluation

`no_signal_counters_daily.csv`

- aggregate NO_SIGNAL counts

`health_rollup_daily.csv`

- daily evaluated bars, signals, NO_SIGNAL counts, and blockers

`debug_tail_snapshot.csv`

- rolling recent evaluations only
- suggested rows: 500

## Outputs

- `gold_v3_203_latest_state_sample.json`
- `gold_v3_203_notification_events_rolling_30d_sample.csv`
- `gold_v3_203_trade_signal_ledger_sample.csv`
- `gold_v3_203_trade_result_ledger_schema.csv`
- `gold_v3_203_trade_history_monthly_summary_schema.csv`
- `gold_v3_203_no_signal_counters_daily_hourly_sample.csv`
- `gold_v3_203_health_rollup_daily_sample.csv`
- `gold_v3_203_debug_tail_snapshot_rolling_sample.csv`
- `gold_v3_203_retention_writer_dry_run_plan.md`
- `gold_v3_203_summary.json`
- `gold_v3_203_decision.csv`
- `paste_me.txt`

## Guardrails

- audit-only
- dry-run only
- no source CSV mutation
- no live file mutation outside Stage203 output directory
- no send
- no order
- no AI API
- no live hook
- no payload
- no autotrade
- NO_SIGNAL must not notify
