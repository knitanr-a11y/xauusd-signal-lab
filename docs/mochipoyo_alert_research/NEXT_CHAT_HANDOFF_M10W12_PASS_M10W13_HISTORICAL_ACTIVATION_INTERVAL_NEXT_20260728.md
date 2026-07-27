# MOCHIPOYO Alert Research — M10W12 PASS / M10W13 next

Repo: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/mochipoyo-alert-research`

## Current formal status

`M10W12_PASS_M10W13_FROZEN_HISTORICAL_SHORT_ACTIVATION_INTERVAL_CALIBRATION_READY_AUDIT_ONLY`

New M10 research scope remains **XAUUSD / GOLD only**. M7C remains its separate frozen BTCUSD+XAUUSD background source-fidelity track.

## Frozen forward monitors — keep unchanged

- collector
- M7C
- M8C
- M9V
- M9Y
- M10B
- M10E
- M10P
- M10P2

Immutable starts remain unchanged:
- M9V `2026.07.24 11:04:00`
- M9Y `2026.07.24 12:45:00`
- M10B `2026.07.24 20:54:00`
- M10E `2026.07.24 22:06:00`
- M10P `2026.07.24 23:56:00`
- M10P2 `2026.07.27 01:39:00`

M10P and M10P2 BAT03 restart was already verified in M10W11. Keep both BAT03 loops running. **Never run either BAT01.**

## M10W12 uploaded result

Package: `99_UPLOAD_PACKAGE(52).zip`  
SHA256: `4c7420ac6210809daee9dc5a783753922c9a807d2a5445f98173f89e14041dbe`  
Status: `PASS_READ_ONLY_THRESHOLD_ACTIVATION_DISTANCE_AUDIT`

Formal result:
`config/mochipoyo_alert_research/m10w12_user_local_threshold_activation_distance_result_20260728.json`

### M10P C056+G013

Observed window:
- start `2026.07.24 23:56:00`
- cutoff M1 `2026.07.27 21:59:00`
- 21 eligible H1 decisions
- full matches 0
- running-shadow candidate cross-check 0 == 0 PASS

Individual frozen condition activation counts:
- H1 MACD hist >= `3.637199446`: **4/21**
- H1 MACD line <= `-7.667425443`: **0/21**
- H1 ret3 >= `18.70087437`: **6/21**
- D1 MACD hist >= `-14.25480242`: **21/21**

Subgroups:
- seed hist+line: **0**
- regime ret3+D1hist: **6**
- all four: **0**

Primary observed bottleneck: **H1 MACD line condition**.

Closest H1 MACD line observation:
- decision `2026.07.27 21:00:00`
- line `-6.7580187279`
- threshold `<= -7.667425443`
- deficit `0.9094067151 bps`
- but same decision hist `-1.9819973503` and ret3 `0.3925262993`, so 3/4 conditions failed.

There were four decisions (`02:00`–`05:00`) where hist + ret3 + D1hist all passed and only line failed, but line was strongly positive (`+11.35` to `+31.72 bps`). This is consistent with the frozen setup requiring a particular rebound/negative-line phase that has not occurred yet. Do not change the line threshold.

### M10P2 C0212

Observed window:
- start `2026.07.27 01:39:00`
- cutoff M1 `2026.07.27 21:59:00`
- 81 eligible M15 decisions
- full matches 0
- running-shadow candidate cross-check 0 == 0 PASS

Individual frozen condition activation counts:
- H4 EMA20-EMA30 >= `37.61355979 bps`: **0/81**
- H1 ATR percentile100 >= `0.8`: **12/81**

Primary observed bottleneck: **H4 EMA20-EMA30 trend-strength condition**.

Maximum observed H4 EMA20-EMA30 spread:
- decision `2026.07.27 16:00:00`
- value `9.7854559203 bps`
- threshold `37.61355979 bps`
- deficit `27.8281038697 bps`

H1 ATR >=80th percentile did occur 12 times, with max observed `0.83`; therefore the ATR leg is alive. Do not lower the H4 threshold.

## Interpretation

- Current zero-match counts are valid current prospective evidence after M10W11 restart verification.
- They are **not performance evidence** because no trades exist yet.
- The detectors are not classified dead.
- The current issue is frozen-condition conjunction/regime non-occurrence.
- No threshold rescue/refit/start change/runtime reset is allowed.

## Next stage — M10W13

Stage:
`M10W13_FROZEN_HISTORICAL_SHORT_ACTIVATION_INTERVAL_CALIBRATION_AUDIT_ONLY`

Purpose:
Use only the already-frozen research-exposed 2023–2026 GOLD raw OHLC context and the exact unchanged formulas to quantify:
- activation counts/rates,
- yearly activation density,
- zero-match decision-run lengths,
- inter-activation spacing,
- p50/p75/p90/p95/p99/max zero-run lengths,
- where current 21 H1 decisions and 81 M15 decisions sit in the historical waiting-time distributions.

It **must not read trade outcomes, PF, PnL, WR, or refit anything**. Historical activation density is waiting-time context only and is not fresh support.

Contract:
`config/mochipoyo_alert_research/m10w13_frozen_historical_short_activation_interval_calibration_contract_20260728.json`

Script:
`scripts/mochipoyo_alert_research/m10w13/python/run_m10w13_frozen_historical_short_activation_interval_calibration.py`

Operator:
`scripts/mochipoyo_alert_research/m10w13/bat/01_run_frozen_historical_short_activation_interval_calibration.bat`

Expected upload:
`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W13\LATEST\99_UPLOAD_PACKAGE.zip`

## Hard prohibitions

- Do not stop/reset/reinitialize existing monitors.
- Never run M10P BAT01 or M10P2 BAT01.
- Do not change C056/G013 or C0212 thresholds/formulas from M10W12 near-misses.
- Do not backfill forward gaps.
- Do not use M10W13 historical waiting-time context as fresh efficacy evidence.
- Do not execute M10V before **both M10P and M10P2 have >=20 resolved trades with integrity PASS**.
- No Discord send, MT5 order, live_ready, final_signal, or automatic live promotion.
