# BTC AI V1 — OHLC Phase-Conditional Expert Result

Date: 2026-08-03  
Status: `COMPLETE_NO_FORMAL_SURVIVOR`

## Method

- XM `BTCUSD#` OHLC only; no external data or volume features.
- one LightGBM expert per outcome-blind phase and direction.
- model fitting, score calibration and event emission were isolated inside each phase.
- 48 raw definitions, 42 capability survivors and 336 exact-M1 exit evaluations.
- development covered 24 calendar months, 2024-01 through 2025-12.

## Aggregate result

- positive-net configurations: 143 / 336
- PF >= 1.20 configurations: 32 / 336
- formal survivors: 0

## Strongest configurations

| Candidate | Phase | Side | Threshold | Policy | Exit | Trades/24m | Trades/month | PF | Net | Positive months | Positive half-years |
|---|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| `PX7_008` | EARLY_IMPULSE | LONG | P90 | FIRST_CROSS_WITHIN_PHASE | S1.0/T2.0/H480 | 64 | 2.67 | 1.4538 | +3,797.81 | 13/24 | 4/4 |
| `PX7_003` | RANGE_NEUTRAL | LONG | P95 | COOLDOWN4_WITHIN_PHASE | S0.75/T2.0/H480 | 268 | 11.17 | 1.3704 | +15,805.22 | 17/24 | 4/4 |

## Why none passed

- `EARLY_IMPULSE LONG` reached PF 1.4538 and was positive in all four half-years, but completed only 64 trades over 24 months (2.67/month), below the frozen minimum of 96.
- `RANGE_NEUTRAL LONG` reached PF 1.3704 with 268 trades (11.17/month), 17 positive months and four positive half-years. However almost all gross profit belonged to `OTHER_TRANSITION`, so the frozen maximum transition gross-profit share of 60% was not met.
- That concentration is partly structural: a phase-specific expert can map predominantly to one transition type. The gate was not changed after seeing the result.
- leave-one-transition-out, bootstrap, matched-random and 2026 diagnosis were not opened because there was no formal development survivor.

## Formal conclusion

`PHASE_CONDITIONAL_SCORING_SHOWED_VALUE_BUT_TRANSFER_CONTRACT_NOT_SATISFIED`

The phase-separated score scale appears more promising than one global score, but this cycle does not support a candidate. A distinct transition-specific expert cycle is required to test the reciprocal design: one expert per transition type, with transfer tested across D1 up/neutral/down regimes.
