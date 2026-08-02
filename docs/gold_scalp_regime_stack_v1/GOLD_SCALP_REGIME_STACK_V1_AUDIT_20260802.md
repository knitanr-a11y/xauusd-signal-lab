# GOLD SCALP REGIME STACK V1 — Research Audit

Date: 2026-08-02  
Formal status: **`RETROSPECTIVE_REGIME_SPECIALIST_STACK_COMPLETE_NO_FORMAL_PORTFOLIO`**

## User boundary

- Existing GOLD candle data only.
- MT5 broker-server naive time.
- Standard spread **0.30 USD once**.
- Initial SL no greater than 5 USD.
- TP no lower than 5 USD.
- Breakeven movement allowed.
- Exact M1 outcome resolution and protective-stop-first same-minute handling.
- Target portfolio median at least 20 trades/month, positive-PnL win rate at least 50%, PF at least 1.20.

## Design

The study tested the proposed architecture rather than one universal model:

1. causally classify each M5 decision into six regimes;
2. maintain structural event specialists by regime, side and exit;
3. select specialists only from fully prior data at each half-year boundary;
4. globally remove simultaneous and overlapping positions;
5. compare regime switching with the same architecture without regime separation;
6. add fail-closed guards and pseudo-forward candidate promotion diagnostics.

Six regimes:

- `TREND_ALIGNED_HIGH`
- `TREND_ALIGNED_NORMAL`
- `TREND_CONFLICT`
- `RANGE_LOW`
- `RANGE_ACTIVE`
- `TRANSITION`

Fourteen event families included HTF pullback resume, micro impulse continuation, run pullback/fade, sweep/reclaim, false-break fade, compression release, breakout hold, volume absorption, effort/result continuation, M5 gap fill, EMA snapback, M15 boundary momentum and round-five-dollar rejection.

Eight exits covered TP5–10, SL2.5–5 and three breakeven variants.

Candidate rows: **170,664**.

Pseudo-forward blocks:

- 2023H2
- 2024H1
- 2024H2
- 2025H1
- 2025H2
- 2026H1
- 2026JUL

Each block used only data before its start for specialist selection.

## Main walk-forward result

The best configuration that met the frequency target was the regime-separated conservative profile:

- trades: **807**
- median monthly trades: **20.0**
- positive-PnL win rate: **39.28%**
- PF: **0.9489**
- net: **-95.33 USD**
- DD: **223.61 USD**
- positive months: **17/37**

| Block | n | WR | PF | Net |
|---|---:|---:|---:|---:|
| 2023H2 | 247 | 45.34% | 0.845 | -64.04 |
| 2024H1 | 128 | 35.16% | 0.776 | -82.13 |
| 2024H2 | 153 | 37.91% | 1.001 | +0.33 |
| 2025H1 | 94 | 41.49% | 1.215 | +56.81 |
| 2025H2 | 125 | 31.20% | 0.822 | -57.30 |
| 2026H1 | 53 | 41.51% | 1.434 | +56.00 |
| 2026JUL | 7 | 28.57% | 0.800 | -5.00 |

The comparable no-regime conservative configuration produced 430 trades, median 10/month, PF 0.914 and net -95.08. Regime separation improved diversification and some later blocks, but did not create a profitable complete portfolio.

## Fail-closed diagnostics

| Variant | n | Median/month | WR | PF | Net |
|---|---:|---:|---:|---:|---:|
| None | 807 | 20 | 39.28% | 0.949 | -95.33 |
| Previous-block guard | 803 | 19 | 39.35% | 0.946 | -100.33 |
| Trailing-20 guard | 427 | 11 | 37.94% | 0.921 | -81.62 |
| Combined | 423 | 11 | 38.06% | 0.916 | -86.62 |

Recent performance guards reduced activity and DD but did not improve PF.

## Candidate-promotion diagnostic

All selected event families were paper-tracked in each pseudo-forward block. A family could trade the next block only after prior paper evidence.

| Promotion rule | n | Median/month | WR | PF | Net | DD |
|---|---:|---:|---:|---:|---:|---:|
| One prior block | 234 | 6 | 38.89% | 1.082 | +50.69 | 85.81 |
| Two prior blocks | 80 | 0 | 38.75% | **1.296** | +56.93 | 34.00 |
| Strict two-block | 67 | 0 | 37.31% | 1.280 | +47.93 | 40.00 |

Promotion improved PF and reduced DD, but frequency collapsed. It is useful as a candidate-development mechanism, not as the requested monthly portfolio.

## Descriptive stable core — not a formal candidate

After the complete walk-forward was visible, three families had positive aggregate contributions:

- `M5_GAP_FILL`
- `COMPRESSION_RELEASE`
- `EFFORT_RESULT_CONT`

Their descriptive combined result was:

- trades: **226**
- win rate: **42.48%**
- PF: **1.2918**
- net: **+160.07 USD**
- DD: **71.61 USD**
- median monthly trades: **7.0**
- positive months: **15/37**

This is post-result descriptive evidence and must not be presented as untouched validation. The frequency is below 20/month and 2025H2 was negative.

## Interpretation

- Regime separation improved some periods and exposed environment-specific specialists.
- No fixed specialist-selection profile remained profitable across all environments.
- Recent-performance kill switches did not solve the problem.
- Promotion based on prior pseudo-forward evidence improved PF but reduced frequency too far.
- Stable candidate accumulation remains more credible than one universal high-frequency model, but more independently sourced candle-only engines are required.

## Formal decision

`NO_FORMAL_PORTFOLIO`

Do not rescue by deleting losing blocks, interpolating thresholds, or restoring only the three descriptive winners as if they were preregistered.

## Next materially distinct boundary

The next candle-only study should estimate **joint first-passage distributions** rather than classify wins directly:

- probability and expected time to +5, +7.5 and +10 USD;
- probability and expected time to -2.5, -3.5 and -5 USD;
- event direction remains structural;
- abstain when favorable and adverse first-passage distributions overlap;
- add resulting engines to the candidate catalog only after multi-block pseudo-forward evidence.

No Shadow, Discord, MT5 order, live trading, promotion or merge authorization follows from this study. Frozen V19 and Challenger C1 were not modified.
