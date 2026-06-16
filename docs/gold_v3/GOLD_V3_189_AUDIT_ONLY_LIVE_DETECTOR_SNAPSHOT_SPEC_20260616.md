# GOLD V3 Stage189 Audit-only Live Detector Snapshot Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage189 creates an audit-only latest closed-row detector snapshot for the Stage187 PRIMARY ABC CAP portfolio.

It does not send Discord, does not place MT5 orders, does not call AI API, does not emit live payload, and does not enable autotrade.

## Primary candidates and priority

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

## CSV contract

CSV latest row is treated as CLOSED.

Open/as-of interpretation is prohibited.

## Snapshot fields

- latest closed M15 time
- priority signal
- fired candidates
- selected candidate
- entry reference price
- TP/SL reference prices
- key features
- A/C/B booleans
- audit safety flags

## Outputs

- `gold_v3_189_latest_detector_snapshot.json`
- `gold_v3_189_latest_detector_snapshot.csv`
- `gold_v3_189_candidate_signal_rows.csv`
- `gold_v3_189_recent_detector_tail.csv`
- `gold_v3_189_audit_only_message_preview.txt`
- `gold_v3_189_source_coverage.csv`
- `gold_v3_189_summary.json`
- `gold_v3_189_decision.csv`
- `paste_me.txt`

## Guardrails

- audit-only
- review-only
- source CSV not mutated
- contract not mutated
- open/as-of not allowed
- candidate pool not removed
- F002 exclusion not bypassed
- final live not enabled
- Discord disabled
- MT5 order disabled
- AI API disabled
- live hook disabled
- payload disabled
- autotrade disabled
- NO_SIGNAL Discord notification disabled
