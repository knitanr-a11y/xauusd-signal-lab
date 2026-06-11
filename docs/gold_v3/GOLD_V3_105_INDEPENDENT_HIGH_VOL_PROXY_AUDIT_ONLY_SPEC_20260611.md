# GOLD V3 Stage105 — Independent High-Vol Proxy Audit-Only Spec

Created JST: `2026-06-11`

Stage name:

`GOLD_V3_105_INDEPENDENT_HIGH_VOL_PROXY_AUDIT_ONLY`

READY status:

`GOLD_V3_105_INDEPENDENT_HIGH_VOL_PROXY_READY_AUDIT_ONLY`

## Purpose

Evaluate whether an independent high-volatility entry universe can restore candidate frequency after Stage104 confirmed the current high-vol siblings are not selecting true high-vol rows.

This stage is proxy-only and audit-only. It does not modify Stage45, Stage69, Stage68, the candidate pool, source CSVs, or any live path.

## Independent high-vol universe

Rows are selected from closed M15 candles where:

```text
is_high_vol == True
```

using Stage50 rolling prior-60D q70 state as the source of the high-vol flag.

## Proxy profiles

The stage creates proxy opportunities for high-vol rows using existing exploratory HV profiles:

- `HV_TP180_SL70_H128`
- `HV_TP200_SL80_H128`
- `HV_TP220_SL90_H128`

It evaluates completed M5 horizons only. Incomplete horizons are excluded from evaluated metrics.

## Segments

The output is grouped by:

- profile
- JST weekday
- JST hour
- H4 return sign bucket

## Outputs

Folder:

`FX_OUTPUTS/gold_v3/105c/`

Files:

- `paste_me.txt`
- `summary.json`
- `independent_high_vol_proxy_opportunities.csv`
- `independent_high_vol_proxy_evaluated_trades.csv`
- `profile_metrics.csv`
- `weekday_metrics.csv`
- `hour_metrics.csv`
- `h4_bucket_metrics.csv`
- `validation.csv`
- `blockers.csv`
- `report.md`

## Safety

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, final signal, source CSV mutation, candidate pool mutation, or manual candidate demotion/removal.
