# GOLD SCALP RETAINED CANDIDATE REGISTRY V1

Date: 2026-08-02  
Formal status: **`RESEARCH_ONLY_RETAINED_CANDIDATE_REGISTRY_NO_DEPLOYMENT`**

## Purpose

This registry consolidates all candle-only GOLD scalp components that previous studies explicitly retained for prospective observation, provisional observation, or descriptive research. It is the canonical retrieval index for future candidate-stack work.

It does **not** turn observation rows into deployable candidates.

## Tier definitions

- `PROSPECTIVE_CATALOG`: survived an earlier calibration and later evaluation sample, but remains too sparse for deployment.
- `PROVISIONAL_OBSERVATION_LEAD`: promising retrospective multi-block component that still lacks a fresh no-backfill period.
- `OBSERVATION_ONLY`: isolated positive evidence, tiny sample, single block, or user-rejected sparse model.
- `DESCRIPTIVE_ONLY`: identified after results were visible; useful only as a hypothesis family.
- `do_not_restore_registry`: failed forward or complete-vector rows that must not be silently resurrected.

## Current retained inventory

- 2 prospective-catalog rows.
- 2 provisional activation/retest observation leads.
- 8 observation-only rows.
- 3 descriptive-only hypothesis-family rows.
- 15 total registry records.

## Strongest retained components

### M5 gap-fill LONG logistic

- TP5 / SL3.
- Calibration: 23 trades, WR 56.52%, PF 1.2068.
- 2025+ evaluation: 26 trades, WR 57.69%, PF 2.1623.
- Low frequency; prospective catalog only.

### Daily reopen gap-down reclaim LONG logistic

- TP5 / SL3.
- Calibration: 13 trades, WR 76.92%, PF 3.2073.
- 2025+ evaluation: 28 trades, WR 50.00%, PF 1.6363.
- Very low frequency; prospective catalog only.

### Volume absorption SHORT activation/retest

Two observation subengines share the same structural family:

1. frozen activation-level reclaim;
2. favorable-extreme pullback resume.

Shared boundary:

- 3 USD favorable activation within 15 minutes before 1 USD adverse travel;
- initial SL 5 USD;
- 50% exit at +5 USD;
- remaining 50% moved to breakeven;
- final target +10 USD;
- horizon 240 minutes.

Observed aggregates:

- level reclaim: 19 trades, WR 63.16%, PF 1.7143, +25 USD;
- extreme resume: 41 trades, WR 60.98%, PF 1.6563, +52.5 USD.

These were isolated after broad-vector results were visible and remain observation-only.

## Dedupe rule

Rows with the same `dedupe_group` represent related evidence or alternative implementations. They must not be counted as independent engines. Exact trade timestamps and one-position overlap must be checked before any portfolio claim.

Examples:

- all daily-reopen gap reclaim rows share one group;
- first-passage and regime descriptive M5 gap-fill rows overlap conceptually with the M5 gap family;
- the two volume-absorption activation/retest rows are sibling subengines.

## Source of truth

Every row includes:

- source branch;
- source PR;
- source file;
- evidence scope;
- status;
- deployment prohibition.

Use `source_registry_20260802.json` to jump back to the originating research.

## Non-restoration rule

The separate `do_not_restore_registry_20260802.csv` records failed fixed-threshold stacks, failed path-shape engines, failed complete research vectors, and broad activation/retest portfolios. They are not fallback candidates.

## Future additions

A new row may be added only when:

1. its hypothesis is independently preregistered;
2. its direction and exit contract are frozen before the target block;
3. exact M1 resolution uses spread 0.30 USD once;
4. it is evaluated through sequential pseudo-forward;
5. related rows receive the same `dedupe_group`;
6. it remains research-only until explicitly authorized.

## Prohibitions

- No Shadow.
- No Discord notifier.
- No MT5 order or live trading.
- No production merge.
- No silent threshold rescue.
- No summing related records as independent candidates.
- No modification of frozen V19 or Challenger C1.
