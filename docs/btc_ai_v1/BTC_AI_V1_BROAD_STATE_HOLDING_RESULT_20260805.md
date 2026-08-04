# BTC AI V1 — Broad state-holding research result

Date: 2026-08-05  
Branch: `feature/btc-broad-state-holding-research`  
Preregistration commit: `0b8661e75dfd0e0f47edf2f99cfecc567faad376`

## Formal conclusion

`BTC_AI_V1_BROAD_STATE_HOLDING_ALL_FORMAL_GATES_REJECTED_H4_DAY_OPEN_CONTINUATION_RETAINED_AS_LEAD`

The entry universe remained broad, but repeated same-direction entries were removed. A position was held while the desired H1/H4 state remained unchanged and was reversed only when the state flipped. A stopped position remained flat until the next state flip.

No family passed every frozen formal gate. However, the H4 broker-day-open displacement continuation state produced positive cost-adjusted results with both 2 ATR and 4 ATR stops and is retained as an independent research lead, not as an adopted candidate.

## Formal period 2024–2026 July

| Family | Risk translation | Trades | PF | Net USD | Max DD | Net/DD |
|---|---|---:|---:|---:|---:|---:|
| H1 body-state continuation | no stop | 11,767 | 0.833 | -353,239.95 | 355,538.62 | -0.994 |
| H1 body-state continuation | 2 ATR stop | 11,768 | 0.848 | -308,781.73 | 310,756.44 | -0.994 |
| H1 body-state continuation | 4 ATR stop | 11,768 | 0.836 | -345,406.09 | 346,778.02 | -0.996 |
| H1 body-state fade | no stop | 11,767 | 0.910 | -176,275.05 | 183,292.82 | -0.962 |
| H1 body-state fade | 2 ATR stop | 11,768 | 0.888 | -209,160.52 | 216,183.91 | -0.968 |
| H1 body-state fade | 4 ATR stop | 11,768 | 0.896 | -203,026.58 | 209,688.08 | -0.968 |
| H4 day-open continuation | no stop | 1,356 | 0.974 | -18,677.74 | 51,693.83 | -0.361 |
| H4 day-open continuation | 2 ATR stop | 1,357 | 1.080 | +38,861.76 | 36,599.83 | 1.062 |
| H4 day-open continuation | 4 ATR stop | 1,357 | 1.063 | +39,432.64 | 30,951.26 | 1.274 |
| H4 day-open fade | no stop | 1,356 | 0.940 | -42,342.26 | 87,469.94 | -0.484 |
| H4 day-open fade | 2 ATR stop | 1,357 | 0.901 | -43,707.56 | 66,186.18 | -0.660 |
| H4 day-open fade | 4 ATR stop | 1,357 | 0.955 | -26,831.44 | 75,849.62 | -0.354 |

## Retained lead

`H4_DAY_OPEN_DISPLACEMENT_STATE_CONTINUATION`

At each fully closed H4 decision:

- desired LONG when H4 close is above that broker-day open
- desired SHORT when H4 close is below that broker-day open
- keep holding while the desired state is unchanged
- reverse only when the state flips
- after a stop, remain flat until the next state flip

### Stress results

| Config | PF | Net USD | Net/DD | Winner-removed PF | Double-cost PF |
|---|---:|---:|---:|---:|---:|
| 2 ATR stop | 1.080 | +38,861.76 | 1.062 | 1.054 | 1.016 |
| 4 ATR stop | 1.063 | +39,432.64 | 1.274 | 1.043 | 1.014 |

### Year slices

| Config | 2024 | 2025 | 2026 Jan–Jul |
|---|---:|---:|---:|
| 2 ATR stop | PF 0.926 / -14,031.81 | PF 1.220 / +44,592.03 | PF 1.088 / +8,301.54 |
| 4 ATR stop | PF 0.926 / -18,211.21 | PF 1.154 / +40,036.78 | PF 1.150 / +17,607.07 |

### Direction slices

| Config | LONG | SHORT |
|---|---:|---:|
| 2 ATR stop | PF 1.194 / +48,039.23 | PF 0.962 / -9,177.47 |
| 4 ATR stop | PF 1.117 / +37,429.21 | PF 1.007 / +2,003.44 |

## Why it remains a lead only

- combined PF did not reach the frozen 1.15 threshold
- Net/DD did not reach 1.50
- 2024 was negative for both stop versions
- winner-removed PF did not reach 1.10
- double-cost PF did not reach 1.05
- July 2026 was negative for both stop versions
- no direction, year, month, hour or volatility slice may be removed after outcomes

## Audit

- raw state decisions: 77,672
- completed trades: 109,712
- unresolved end-of-data positions: 4
- missing exact decision M1 events: 22
- no next-M1 fallback
- synthetic state-machine tests: 2 passed
- reference Python versus Numba parity: first 500 H4 events, 122 trades, exact match
- future/open/as-of feature use: 0
- Stage55 modified: false

## Next boundary

Do not create a prospective Shadow from this result. The next research should test entry-time-known state duration, broker-day transition and broker-week open relationships without selecting the profitable years or LONG direction after the fact.

MT5 orders, live trading, live-ready, final signal, Discord and automatic promotion remain OFF.
