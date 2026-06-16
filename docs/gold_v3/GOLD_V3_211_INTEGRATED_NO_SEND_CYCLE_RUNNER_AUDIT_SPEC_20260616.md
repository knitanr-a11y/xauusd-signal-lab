# GOLD V3 Stage211 Integrated No-Send Cycle Runner Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage211 rebuilds the latest dry-run cycle directly from closed OHLC.

It combines detector rebuild, route decision, identity generation, latest-state preview, append previews, counter preview, and health preview in one stage.

## Integrated flow

1. Read closed M15/H1/H4/D1 candles.
2. Build features using the Stage177 feature contract.
3. Detect PRIMARY ABC candidates.
4. Detect SECONDARY_AUDIT_CANDIDATE candidates.
5. Decide final route with PRIMARY priority.
6. Generate signal_id and short_signal_id only when SIGNAL exists.
7. Build latest_state preview.
8. Build trade_signal append preview only when SIGNAL exists.
9. Build notification append preview only when SIGNAL exists.
10. Build NO_SIGNAL counter preview when NO_SIGNAL exists.
11. Build health rollup preview.

## Outputs

- `gold_v3_211_source_coverage.csv`
- `gold_v3_211_primary_detector_entries.csv`
- `gold_v3_211_secondary_detector_entries.csv`
- `gold_v3_211_integrated_tail96.csv`
- `gold_v3_211_latest_state_integrated_preview.json`
- `gold_v3_211_trade_signal_append_integrated_preview.csv`
- `gold_v3_211_notification_append_integrated_preview.csv`
- `gold_v3_211_no_signal_counter_integrated_preview.csv`
- `gold_v3_211_health_rollup_integrated_preview.csv`
- `gold_v3_211_integrated_write_plan.csv`
- `gold_v3_211_integrated_validation_checks.csv`
- `gold_v3_211_debug_tail_integrated_preview.csv`
- `gold_v3_211_integrated_no_send_cycle_plan.md`
- `gold_v3_211_summary.json`
- `gold_v3_211_decision.csv`
- `paste_me.txt`

## Guardrails

- audit-only
- dry-run only
- no live retention file mutation
- no source CSV mutation
- no actual import
- no execution
- no send
- no AI API
- no live hook
- no payload
- no autotrade
- NO_SIGNAL must not notify
