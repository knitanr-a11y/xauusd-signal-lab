# GOLD Scalp Daily / Session Geometry V1 — V19 / Challenger C1 Overlap Audit

Date: 2026-08-02

Formal conclusion:

`ENTRY_GENERATION_INDEPENDENT_BUT_NO_FORMAL_CANDIDATE`

## Scope

The user authorized a new candle-only research line only if it did not duplicate or modify frozen V19 or Challenger C1. This audit distinguishes:

1. implementation or state-path overlap;
2. feature and entry-grammar overlap;
3. possible coincident timestamps.

## V19 boundary

Frozen V19 enters only when all of the following are present:

- the E40 HTF direction router;
- trailing-60-day direction-specific P90 rank;
- causal multi-scale wave state `IMPULSE_EARLY`;
- first eligible P90 observation per wave episode;
- TP20 / SL10 / exact 480-M1 execution.

Daily / Session Geometry V1 does not read, calculate, import, or filter on E40 scores, P90 ranks, V19 wave states, V19 episode IDs, V19 accepted entries, or V19 runtime state.

## Challenger C1 boundary

Challenger C1 uses the frozen V19 router, states `IMPULSE_LATE` and `CORRECTION_EARLY`, `chosen_rank < 0.90`, first causal transition onset, TP20 / SL10, and V19 priority/preemption.

Daily / Session Geometry V1 does not read, calculate, import, or filter on Challenger wave eligibility, chosen rank, transition onset, V19 priority, or preemption state.

## Independent Geometry V1 entry grammar

The research creates entries only from levels fixed independently of V19 and Challenger outcomes:

- completed previous-day high and low;
- fixed MT5 server-hour opening ranges beginning at 01:00, 08:00, and 15:00;
- daily reopen gap level;
- closed-M5 sweep, close-back, expansion, retest, or gap-hold confirmation;
- next exact M1 open after confirmation.

It uses no ML model, no score rank, no wave grammar, and no existing-candidate episode state.

## Repository and runtime isolation

- Research base: `main`.
- Dedicated namespace: `gold_scalp_daily_session_geometry_v1`.
- V19 modified: false.
- Challenger C1 modified: false.
- P75 State Survival Shadow modified: false.
- No runtime state directory is created.
- No Shadow, Discord, order, or continuous monitor is implemented.

## Timestamp caveat

The entry-generation logic is independent. This does not claim that two independent systems can never produce an entry at the same timestamp. A timestamp-level portfolio overlap study would require authoritative historical V19 and Challenger accepted-entry ledgers as explicit read-only comparison inputs. Those ledgers were not used as candidate inputs in this research.

## Result

The independent family condition was satisfied, but performance failed:

- exact-M1 pseudo-forward selected trades: 33;
- win rate: 45.45%;
- PF: 0.78125;
- net: -15.75 USD;
- max drawdown: 32.25 USD;
- formal observation candidates: zero.

Therefore the family is recorded as completed negative research and is not added to Shadow or the retained-candidate registry.
