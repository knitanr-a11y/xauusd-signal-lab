# GOLD V3 Stage202 No-Signal Retention and Clean Outputs Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage202 finishes preview formatting and defines practical live retention for NO_SIGNAL.

It does not change signal rules, scoring, portfolio selection, or any live behavior.

## Practical retention policy

Do not append every NO_SIGNAL full row forever.

Recommended live files:

1. `latest_state.json`
   - overwrite every evaluation
   - latest closed M15 time, PRIMARY route, SECONDARY_AUDIT_CANDIDATE route, and safety flags

2. `signal_events.csv`
   - append only when PRIMARY or SECONDARY_AUDIT_CANDIDATE signal exists

3. `no_signal_counters_daily.csv`
   - aggregate NO_SIGNAL counts by date, hour, role, and route

4. `health_rollup_daily.csv`
   - aggregate evaluated bars, signal bars, NO_SIGNAL bars, missing-data bars, and blocker bars

5. `debug_tail_snapshot.csv`
   - rolling last N evaluations only
   - suggested N: 500

## Inputs

- Stage201 latest compact preview
- Stage201 tail96 compact signal rows
- Stage201 latest role preview
- Stage201 decision
- Stage200 tail96 preview

## Outputs

- `gold_v3_202_latest_compact_preview_clean.csv`
- `gold_v3_202_tail96_signal_rows_compact_clean.csv`
- `gold_v3_202_latest_role_preview_clean.csv`
- `gold_v3_202_no_signal_counters_daily_hourly_from_tail96.csv`
- `gold_v3_202_health_rollup_daily_from_tail96.csv`
- `gold_v3_202_latest_state_sample.json`
- `gold_v3_202_no_signal_retention_policy.md`
- `gold_v3_202_summary.json`
- `gold_v3_202_decision.csv`
- `paste_me.txt`

## Pass conditions

- blocker_count == 0
- clean display CSV outputs do not contain `nan` text
- clean display CSV outputs do not contain legacy secondary label text
- no send enabled
- no order enabled
- no payload/live hook/autotrade enabled
- NO_SIGNAL remains non-notifying

## Guardrails

- audit-only
- review-only
- no source CSV mutation
- no contract mutation
- no open/as-of interpretation
- no candidate pool removal
- no F002 bypass
- no final live approval
- no send
- no order
- no AI API
- no live hook
- no payload
- no autotrade
- NO_SIGNAL must not notify
