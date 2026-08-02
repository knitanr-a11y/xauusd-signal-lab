# GOLD SCALP RETAINED CANDIDATE REGISTRY V1

Date: 2026-08-02  
Formal status: **`RESEARCH_ONLY_RETAINED_CANDIDATE_REGISTRY_NO_DEPLOYMENT`**

## Purpose

This registry consolidates all candle-only GOLD scalp components that previous studies explicitly retained for prospective observation, provisional observation, or descriptive research. It is the canonical retrieval index for future candidate-stack work.

It does **not** turn observation rows into deployable candidates.

## Authoritative catalog

- Current authoritative registry: `retained_candidate_catalog_20260802_v2.csv`.
- Records: 17.
- The original 15-record CSV and JSON remain audit snapshots.
- Generate current JSON through `export_registry.py` from the v2 CSV.

## Tier definitions

- `PROSPECTIVE_CATALOG`: survived an earlier calibration and later evaluation sample, but remains too sparse for deployment.
- `PROVISIONAL_OBSERVATION_LEAD`: promising retrospective multi-block component that still lacks a fresh no-backfill period.
- `OBSERVATION_ONLY`: isolated positive evidence, tiny sample, single block, or user-rejected sparse model.
- `DESCRIPTIVE_ONLY`: identified after results were visible; useful only as a hypothesis family.
- `do_not_restore_registry`: failed forward or complete-vector rows that must not be silently resurrected.

## Current retained inventory

- 2 prospective-catalog rows.
- 4 provisional activation/retest observation leads.
- 8 observation-only rows.
- 3 descriptive-only hypothesis-family rows.
- 17 total registry records.

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

Observed pseudo-forward aggregates:

- level reclaim: 19 trades, WR 63.16%, PF 1.7143, +25 USD;
- extreme resume: 41 trades, WR 60.98%, PF 1.6563, +52.5 USD.

These were isolated after broad-vector results were visible and remain observation-only.

### Trend LONG activation/retest

Two additional observation leads use the same staged exit but different structural causes:

1. effort/result continuation LONG;
2. HTF pullback resume LONG.

Shared entry boundary:

- H1/H4-aligned trend regime;
- +3 USD favorable travel within 15 minutes before 1 USD adverse travel;
- 1 USD retest through the frozen activation level;
- bullish close back above the activation level;
- next M1 open.

Complete natural-history descriptive results:

- effort/result continuation: 53 trades, WR 60.38%, PF 1.7001, +68.42 USD, DD 20.23 USD;
- HTF pullback resume: 47 trades, WR 65.96%, PF 2.0820, +86.56 USD, DD 15 USD.

These exact rows were isolated after the broad LONG/range results were visible. They have no fresh no-backfill target and remain provisional observation leads.

## Descriptive four-lead stack

The two Trend LONG leads and the two VOLUME_ABSORPTION SHORT leads produced, after global one-position overlap removal:

- 249 trades;
- WR 57.43%;
- PF 1.4547;
- net +232.84 USD;
- DD 30.35 USD;
- median six trades/month.

All half-year blocks from 2023H1 through 2026JUL were positive, but this stack was formed after all four components were visible. It is architecture evidence only, not validation or deployment evidence.

## Dedupe rule

Rows with the same `dedupe_group` represent related evidence or alternative implementations. They must not be counted as independent engines. Exact trade timestamps and one-position overlap must be checked before any portfolio claim.

Examples:

- all daily-reopen gap reclaim rows share one group;
- first-passage and regime descriptive M5 gap-fill rows overlap conceptually with the M5 gap family;
- the two volume-absorption activation/retest rows are sibling subengines;
- the two Trend LONG rows have separate causes and separate groups, but the descriptive four-lead stack still requires exact overlap removal.

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

The separate `do_not_restore_registry_20260802.csv` records failed fixed-threshold stacks, failed path-shape engines, failed complete research vectors, broad activation/retest portfolios, and the rejected range follow/failure families. They are not fallback candidates.

## Future additions

A new row may be added only when:

1. its hypothesis is independently preregistered;
2. its direction and exit contract are frozen before the target block;
3. exact M1 resolution uses spread 0.30 USD once;
4. it is evaluated through sequential pseudo-forward;
5. related rows receive the same `dedupe_group`;
6. it remains research-only until explicitly authorized.

## Next research boundary

The next independent family is session/daily-level geometry:

- previous-day high/low sweep and close-back;
- session opening-range expansion and first retest;
- daily reopen gap interaction;
- one eligible trade per frozen level per session.

## Prohibitions

- No Shadow.
- No Discord notifier.
- No MT5 order or live trading.
- No production merge.
- No silent threshold rescue.
- No summing related records as independent candidates.
- No modification of frozen V19 or Challenger C1.
