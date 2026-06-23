# GOLD V3 Stage313 — Fragility and Diversification Audit

## Purpose

Stage312 produced one formal research pass, but that pass failed the 2026 stress check and showed strong quarter concentration. Stage313 therefore does not register or promote it. It audits fragility and tests whether a second, differently behaving Mochipoyo track improves stability.

## Frozen primary

- family: `M5_H4|MOCHI_HIDDEN_PULLBACK|LONG|RR1_5`
- filter: `quality_score >= 8.0`
- origin: the only Stage312 formal pass

## Frozen secondary

- family: `M5_H4|MOCHI_EARLY_PULLBACK|SHORT|RR1_5`
- filter: `atr_ratio_signal >= 1.0`
- round-number-near entries excluded
- origin: Stage312 low-frequency profile with positive 2024, 2025, and 2026 results

No threshold search is performed in Stage313.

## Primary fragility tests

- adjacent quality-profile comparison: BASE, 7.5, 8.0, 8.5
- quarterly contribution concentration
- selection result after removing the best quarter
- leave-one-quarter-out summaries
- rolling six-month windows, advanced one month at a time
- 2026 stress result retained from the frozen trade set

The primary is retained only when:

- the Stage312 formal gate passed
- the 2026 stress gate passed
- at least half of selection quarters are positive
- selection remains positive after removing its best quarter
- at least half of rolling six-month windows are positive

## Secondary research-watch test

The secondary is not allowed to bypass the Stage311 sample gate. It can only become a low-frequency research watch when:

- each of 2024, 2025, and 2026 has at least eight trades
- each year has PF at least 1.15
- each year has positive spread-adjusted R
- aggregate drawdown is no more than 8R
- at least half of rolling six-month windows are positive

This is not candidate-pool registration.

## Diversified one-position replay

The fixed primary and secondary trades are merged with:

- one position at a time
- no preemption
- primary priority before secondary on an exact tie
- a later trade rejected while the accepted trade remains open

A diversified research watch requires:

- at least 15 accepted trades in every year
- PF at least 1.10 and positive R in every year
- aggregate PF at least 1.25
- aggregate drawdown no more than 11R
- at least half of rolling six-month windows positive

Because 2026 was already visible in Stage311 and Stage312, even a passing diversified watch is not a pristine holdout result and cannot be promoted automatically.

## Outputs

- `stage313_fragility_and_diversification_audit.json`
- `stage313_diversified_research_watch_trades.csv`

## Preserved state

- GOLD V3 audit-only
- Stage280 remains blocked
- Stage307 top remains unchanged as a registered research candidate
- Stage292 candidate pool unchanged
- final signal unchanged
- MT5 automatic order OFF
- Discord OFF
- partial close OFF
