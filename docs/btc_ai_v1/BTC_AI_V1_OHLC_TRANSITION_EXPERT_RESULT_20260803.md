# BTC AI V1 — OHLC Transition-Conditional Expert Result

Date: 2026-08-03  
Status: `COMPLETE_NO_FORMAL_SURVIVOR`

## Method

- XM `BTCUSD#` closed-bar OHLC only.
- one LightGBM expert per outcome-blind transition type and direction.
- fitting, calibration and event emission were isolated inside the same transition type.
- transfer was assessed across D1 UP / NEUTRAL / DOWN regimes.
- 48 raw definitions, 26 capability survivors and 208 exact-M1 exit evaluations.
- development: 2024-01 through 2025-12, exactly 24 calendar months.

## Aggregate result

- positive-net configurations: 89 / 208
- PF >= 1.20 configurations: 30 / 208
- full development survivors: 0

## Strongest configurations

| Candidate | Transition | Side | Threshold | Policy | Exit | Trades/24m | Trades/month | PF | Net | Positive months | Positive half-years | D1-regime floor |
|---|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| `TX8_000` | INTO_EARLY_IMPULSE | LONG | P90 | FIRST_CROSS_WITHIN_TRANSITION | S0.75/T2.0/H480 | 78 | 3.25 | 1.6162 | +5,200.22 | 14/24 | 3/4 | False |
| `TX8_037` | EXHAUSTION_TO_REVERSAL | SHORT | P90 | COOLDOWN4_WITHIN_TRANSITION | S0.75/T2.0/H720 | 79 | 3.29 | 1.4931 | +6,755.63 | 12/24 | 2/4 | True |

## Interpretation

- `INTO_EARLY_IMPULSE LONG` reached PF 1.6162, net +5,200.22 and three positive half-years, but completed only 78 trades over 24 months (3.25/month), below the frozen 96-trade minimum. It also failed the D1-regime PF floor.
- `EXHAUSTION_TO_REVERSAL SHORT` reached PF 1.4931, net +6,755.63, but completed only 79 trades (3.29/month), had only 12 positive months and two positive half-years in its top setting.
- Thirty configurations exceeded PF 1.20, but none simultaneously satisfied density, monthly persistence, half-year persistence and D1-regime transfer gates.
- Leave-one-D1-regime-out, bootstrap, matched-random and 2026 diagnosis were not opened because no configuration passed development.

## Formal conclusion

`TRANSITION_EXPERTS_FOUND_HIGH_PF_LOW_DENSITY_LOCAL_EDGES_WITHOUT_TRANSFER_SUPPORT`

The root-cause hypothesis is partially supported: separating early impulse and exhaustion/reversal transitions produces materially stronger local edges than one global score. However those edges are sparse and not yet stable enough across time and D1 regimes to become candidates. No thresholds or minimum-count gates were relaxed.
