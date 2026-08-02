# GOLD SCALP LONG / RANGE ACTIVATION + PARTIAL EXIT V1 — Audit

Date: 2026-08-02  
Formal status: **`RETROSPECTIVE_LONG_RANGE_ACTIVATION_PARTIAL_COMPLETE_TWO_PROVISIONAL_TREND_LONG_LEADS_RANGE_REJECTED_NO_DEPLOYMENT`**

## Contract

- Existing GOLD candle data only.
- MT5 broker-server naive time and closed rows only.
- Exact M1 entry and exit resolution.
- Standard spread: 0.30 USD once.
- Initial SL no greater than 5 USD.
- First target no lower than 5 USD.
- Staged exits only:
  - 50% at +5, remainder breakeven, final +10, SL5;
  - 67% at +5, remainder breakeven, final +10, SL5;
  - 50% at +5, remainder breakeven, final +7.5, SL4.
- One-position non-overlap.
- Half-year pseudo-forward selection.
- No post-result hour, month, or volatility deletion.

## Preregistered families

### Trend LONG

Events:

- HTF pullback resume;
- compression release;
- effort/result continuation.

Only LONG setups in `TREND_ALIGNED_NORMAL` or `TREND_ALIGNED_HIGH` were eligible.

Entry state machine:

- +3 USD favorable activation within 15 minutes;
- activation before 1 USD adverse movement;
- 0.5 or 1.0 USD retest;
- level reclaim or favorable-extreme resume;
- enter next M1 open.

### Range LONG / SHORT

Events:

- range sweep/reclaim;
- round-five-dollar rejection;
- EMA snapback;
- run exhaustion fade.

Only `RANGE_LOW`, `RANGE_ACTIVE`, or `TRANSITION` regimes were eligible.

Entry state machine:

- +2 USD favorable activation within 15 minutes;
- activation before 1 USD adverse movement;
- 0.5 or 1.0 USD retest;
- level reclaim or favorable-extreme resume.

Three causal confirmation tiers were tested: base, strong confirmation, and fast strong confirmation.

## Main pseudo-forward result

No complete portfolio passed.

| Profile | Trades | WR | PF | Net | DD | Median/month |
|---|---:|---:|---:|---:|---:|---:|
| CATALOG | 234 | 47.01% | 0.8817 | -67.86 | 147.55 | 3 |
| BALANCED | 213 | 48.83% | 0.9399 | -30.69 | 108.05 | 3 |

### Family decomposition

| Profile | Family | Trades | WR | PF | Net |
|---|---|---:|---:|---:|---:|
| CATALOG | Trend LONG | 54 | 57.41% | 1.4482 | +51.54 |
| CATALOG | Range LONG | 106 | 47.17% | 0.8677 | -33.53 |
| CATALOG | Range SHORT | 74 | 39.19% | 0.5814 | -85.87 |
| BALANCED | Trend LONG | 47 | 57.45% | 1.4521 | +45.21 |
| BALANCED | Range LONG | 106 | 47.17% | 0.8677 | -33.53 |
| BALANCED | Range SHORT | 60 | 45.00% | 0.7304 | -42.37 |

Activation/retest helped Trend LONG but not range mean reversion.

## Range-failure inversion

A second preregistered study treated the same range setups as failed mean-reversion structures:

- pre-activation adverse failure and close beyond the adverse boundary;
- post-activation collapse back through the setup reference;
- trade in the opposite direction.

Result for both profiles:

- 167 trades;
- WR 46.11%;
- PF 0.9192;
- net -31.42 USD;
- median 7 trades/month;
- no one-block or two-block promoted engine;
- no retained observation row.

Range follow and range-failure continuation are both rejected.

## Provisional Trend LONG leads

Two exact structures remained positive in the pseudo-forward decomposition and were then audited over their complete natural historical occurrences. The complete-history figures are retrospective descriptive, not fresh validation.

### `TREND_LONG_EFFORT_LEVEL_P1_BASE_P50`

- event: effort/result continuation LONG;
- aligned H1/H4 trend regime;
- +3 USD within 15 minutes before -1 USD;
- 1 USD pullback through activation level;
- bullish close back above activation level;
- next M1 open;
- 50% at +5, remainder breakeven, final +10, SL5.

Complete natural descriptive result:

- 53 trades;
- WR 60.38%;
- PF 1.7001;
- net +68.42 USD;
- DD 20.23 USD;
- median 1 trade/month.

Weak blocks included 2024H1 and 2026JUL.

### `TREND_LONG_HTF_LEVEL_P1_BASE_P50`

- event: HTF pullback resume LONG;
- aligned H1/H4 trend regime;
- same activation, retest, entry, and staged exit as above.

Complete natural descriptive result:

- 47 trades;
- WR 65.96%;
- PF 2.0820;
- net +86.56 USD;
- DD 15.00 USD;
- median 1 trade/month.

2026H1 was negative. No fresh no-backfill period exists.

Both are provisional observation leads only.

## Descriptive retained-lead stack

A post-result descriptive stack combined the two Trend LONG leads with the two previously retained VOLUME_ABSORPTION SHORT activation/retest leads. Same-entry and holding overlap were removed globally with deterministic candidate-ID ordering.

- 249 trades;
- WR 57.43%;
- PF 1.4547;
- net +232.84 USD;
- DD 30.35 USD;
- median 6 trades/month;
- 28 positive months;
- 71 simultaneous-entry collisions;
- 101 rows removed by global non-overlap.

| Block | n | WR | PF | Net |
|---|---:|---:|---:|---:|
| 2023H1 | 33 | 57.58% | 1.3046 | +21.33 |
| 2023H2 | 16 | 50.00% | 1.6101 | +18.06 |
| 2024H1 | 25 | 52.00% | 1.2001 | +10.49 |
| 2024H2 | 33 | 57.58% | 1.3334 | +23.34 |
| 2025H1 | 38 | 55.26% | 1.3461 | +29.41 |
| 2025H2 | 54 | 66.67% | 2.2523 | +112.71 |
| 2026H1 | 42 | 52.38% | 1.0500 | +5.00 |
| 2026JUL | 8 | 62.50% | 1.8333 | +12.50 |

This is architecture evidence only. It is not validation because all four components were already visible before the stack was formed.

## Decision

- No complete LONG/range portfolio is authorized.
- Range follow engines: reject.
- Range failure engines: reject.
- Retain the two Trend LONG structures as `PROVISIONAL_OBSERVATION_LEAD` in the unified registry.
- Do not deploy, notify, Shadow, or connect MT5 orders.
- Do not modify V19 or Challenger C1.

## Next boundary

The retained descriptive stack has a median of only six trades/month. The next independent candle-only family should avoid the same activation/retest cause. A suitable boundary is session/daily-level geometry:

- previous-day high/low sweep and close-back;
- session opening-range expansion and first retest;
- daily reopen gap interaction;
- one eligible trade per frozen level per session;
- fixed staged exit and half-year pseudo-forward promotion.
