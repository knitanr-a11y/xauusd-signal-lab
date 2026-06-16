# GOLD V3 Stage186 B_HIGH_FREQUENCY Loss Pattern Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage186 investigates loss patterns in `B_HIGH_FREQUENCY`, which is a PRIMARY candidate in Stage185 and contributes the most extra trade count.

Stage185 showed that the priority unique portfolio remains strong, but weak months such as 2026-02 and 2026-06 may be influenced by B's rougher monthly profile.

## Candidate

`B_HIGH_FREQUENCY`

- rule: `d1_dist_close_atr28<=-0.394892`
- direction: LONG
- TP/SL: 50 / 30
- horizon_m5: 192

## Audits

- monthly profile
- MT5 hour profile
- weekday profile
- weak-month date and week profile
- feature win/loss differences
- h1_atr14 cap sensitivity
- MT5 hour exclusion sensitivity

Weak months reviewed by default:

- 2026-02
- 2026-03
- 2026-06

## Outputs

- `gold_v3_186_b_trades.csv`
- `gold_v3_186_b_monthly.csv`
- `gold_v3_186_b_by_hour_mt5.csv`
- `gold_v3_186_b_by_dow.csv`
- `gold_v3_186_b_weak_months_by_date.csv`
- `gold_v3_186_b_weak_months_by_week.csv`
- `gold_v3_186_b_feature_win_loss.csv`
- `gold_v3_186_b_h1_atr_cap_sensitivity.csv`
- `gold_v3_186_b_hour_exclusion_sensitivity.csv`
- `gold_v3_186_source_coverage.csv`
- `gold_v3_186_summary.json`
- `gold_v3_186_decision.csv`
- `paste_me.txt`

## Time basis

All hour fields are CSV/MT5 timestamp hours. No JST conversion is applied.

## Guardrails

Stage186 is audit-only.

Do not remove B or add a live filter only because one weak month improves. Any proposed filter must be rechecked across full/train/test/recent3m and portfolio overlap in a later stage.

No live signal, payload, Discord, MT5 order, AI API, live hook, or autotrade is enabled.
