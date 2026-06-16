# GOLD V3 Stage190 Handoff and Recent Trade Presence Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage190 creates a formal handoff packet for the current GOLD V3 state and checks whether yesterday or today had PRIMARY ABC CAP entry-signal events.

The recent trade presence check is audit-only and means:

> closed-M15 entry-signal event from the detector

It does not mean a real executed trade, because MT5 orders remain disabled.

## Current primary portfolio

Priority order:

1. `A_PRECISION_BASE`
2. `C_BALANCED_CAP60`
3. `B_HIGH_FREQUENCY_CAP40`

### A_PRECISION_BASE

`d1_dist_close_atr28<=-0.438769 & h4_body_atr14>=0.883347`

LONG TP40 SL20 horizon192

### C_BALANCED_CAP60

`d1_dist_close_atr28<=-0.263261 & h4_body_atr14>=0.530008 & h1_atr14<=60`

LONG TP30 SL30 horizon192

### B_HIGH_FREQUENCY_CAP40

`d1_dist_close_atr28<=-0.394892 & h1_atr14<=40`

LONG TP50 SL30 horizon192

## Date basis

Yesterday and today are calculated from the latest closed M15 row's MT5/CSV date.

No JST conversion is applied.

## Outputs

- `GOLD_V3_190_HANDOFF_PRIMARY_ABC_CAP_AUDIT_ONLY.md`
- `gold_v3_190_yesterday_today_detector_rows.csv`
- `gold_v3_190_yesterday_today_signal_rows.csv`
- `gold_v3_190_yesterday_today_new_signal_events.csv`
- `gold_v3_190_yesterday_today_daily_summary.csv`
- `gold_v3_190_source_coverage.csv`
- `gold_v3_190_summary.json`
- `gold_v3_190_decision.csv`
- `paste_me.txt`

## Guardrails

- audit-only
- review-only
- no GOLD V2 / old GOLD / DISC8 / Stage41
- CSV latest row is CLOSED
- open/as-of interpretation prohibited
- no candidate pool removal
- no F002 bypass
- no final live approval
- no Discord notification
- no MT5 order
- no AI API
- no live hook
- no payload
- no autotrade
- NO_SIGNAL must not notify Discord
