# GOLD V3 Stage188 Primary ABC Cap Live Parity Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage188 checks whether the Stage187 PRIMARY ABC CAP signals can be detected from closed CSV/MT5 OHLC rows in a live-style manner.

It compares:

1. batch feature/signal calculation over the combined OHLC history;
2. stepwise live-style recalculation using only rows with `dt <= target M15 dt`.

The goal is to confirm that recent closed M15 rows produce identical features and signals in both modes.

## Primary candidates and priority

Priority order:

1. `A_PRECISION_BASE`
2. `C_BALANCED_CAP60`
3. `B_HIGH_FREQUENCY_CAP40`

### A_PRECISION_BASE

`d1_dist_close_atr28<=-0.438769 & h4_body_atr14>=0.883347`

### C_BALANCED_CAP60

`d1_dist_close_atr28<=-0.263261 & h4_body_atr14>=0.530008 & h1_atr14<=60`

### B_HIGH_FREQUENCY_CAP40

`d1_dist_close_atr28<=-0.394892 & h1_atr14<=40`

## Compared fields

- `m15_open`
- `m15_high`
- `m15_low`
- `m15_close`
- `h1_atr14`
- `h4_body_atr14`
- `d1_dist_close_atr28`
- `h1_close`
- `h4_close`
- `d1_close`
- A/C/B signal booleans
- fired candidate list
- priority signal

## CSV contract

CSV latest row is treated as CLOSED by contract.

Open/as-of interpretation is prohibited.

## Outputs

- `gold_v3_188_source_coverage.csv`
- `gold_v3_188_batch_latest_rows_with_signals.csv`
- `gold_v3_188_stepwise_live_parity_rows.csv`
- `gold_v3_188_stepwise_feature_compare.csv`
- `gold_v3_188_latest_signal_snapshot.json`
- `gold_v3_188_latest_signal_snapshot.csv`
- `gold_v3_188_summary.json`
- `gold_v3_188_decision.csv`
- `paste_me.txt`

## Guardrails

Stage188 is audit-only.

No source CSV mutation, contract mutation, open/as-of allowance, candidate pool removal, F002 bypass, live signal, payload, Discord, MT5 order, AI API, live hook, or autotrade is enabled.
