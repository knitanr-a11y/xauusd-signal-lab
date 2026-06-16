# GOLD V3 Stage184 C_BALANCED H1 ATR Cap Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage184 tests whether the February 2026 weakness in `C_BALANCED` can be reduced by adding an entry-time `h1_atr14` upper cap.

This is motivated by Stage183, where February 2026 losing trades had materially higher `h1_atr14` than winning trades.

## Candidate

`C_BALANCED`

- rule: `d1_dist_close_atr28<=-0.263261 & h4_body_atr14>=0.530008`
- direction: LONG
- TP/SL: 30 / 30
- horizon_m5: 192

## Tested caps

Default caps:

- no cap
- `h1_atr14 <= 60`
- `h1_atr14 <= 70`
- `h1_atr14 <= 80`
- `h1_atr14 <= 90`
- `h1_atr14 <= 100`
- `h1_atr14 <= 110`
- `h1_atr14 <= 120`

## Acceptance review

Do not accept a cap only because it fixes February 2026.

A useful cap should preserve:

- full trade count;
- train/test/full PF;
- recent3m PF;
- full negative months;
- 2026-02 improvement.

## Time basis

The hour fields from Stage183 are CSV/MT5 timestamp hours. They are not converted to JST unless a later stage explicitly implements such conversion.

## Outputs

- `gold_v3_184_h1_atr_cap_summary.csv`
- `gold_v3_184_monthly_by_cap.csv`
- `gold_v3_184_trades_by_cap.csv`
- `gold_v3_184_source_coverage.csv`
- `gold_v3_184_summary.json`
- `gold_v3_184_decision.csv`
- `paste_me.txt`

## Guardrails

Stage184 is audit-only.

No live signal, payload, Discord, MT5 order, AI API, live hook, or autotrade is enabled.
