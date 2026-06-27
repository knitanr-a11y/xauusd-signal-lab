# MLR2 Candidate Redesign v1 — Label-Free Lock

Status: `MLR2_V1_CANDIDATE_DEFINITIONS_FROZEN_LABEL_FREE_AUDIT_ONLY`

The old MLR1 candidate pool remains unchanged as a historical benchmark. MLR2 introduces ten new candidate IDs across five structural families. Every proposal requires an `environment -> setup -> confirmation` state and is emitted only on an exact false-to-true onset.

No labels, outcomes, R, win rate, PF or model predictions were used to choose these definitions. Only feature availability, event density, calendar-year coverage, same-time overlap and direction conflicts were inspected.

## Families

1. H1 trend pullback resumption;
2. multi-bar compression breakout;
3. failed breakout reclaim;
4. rolling-extreme retest continuation;
5. high-volatility exhaustion turn.

## Frozen label-free result

- ten candidates;
- 3,156 raw proposals;
- 3,041 unique decisions;
- LONG 1,823;
- SHORT 1,333;
- 115 decisions with two same-direction candidates;
- zero LONG/SHORT conflicts;
- maximum two candidates at one decision;
- every candidate has 100–5,000 events and covers 2023, 2024, 2025 and 2026.

Proposal registry SHA256:

`0afe40cf2d856d7fbb195c163efb801ca7f964da9daad6097d14d774af119cfe`

These definitions and this SHA must be committed before ML-03 labels are joined. After the freeze, candidate conditions may not be revised in response to performance. Evaluation must use `GML1-META-CORE v1` unchanged.
