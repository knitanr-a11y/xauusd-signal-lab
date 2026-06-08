# GOLD V2 25C80 OHLC reproduction status summary

Created: 2026-06-08

Status: `OHLC_REPRODUCTION_STATUS_SUMMARY_AUDIT_ONLY`

This document summarizes what is now known after the 25C75-25C80 chain, especially the relationship between existing source-of-truth artifacts, raw RR125 outcomes, uploaded OHLC candles, and whether win-rate/PF are reproduced.

## Guardrails

- GOLD V2 remains audit-only.
- This is not source recovery approval.
- This is not a live evaluator unlock.
- This does not enable Discord, MT5, AI API, live hook, or final signal.
- Old GOLD/DISC8 remains quarantined.
- Approximate reimplementation must not be treated as SOT.

## Current artifact state

| Area | Status | Detail |
| --- | --- | --- |
| A002 event extraction | DONE | 772 audit-only A002 events were produced by the fixed scope chain. |
| A002 raw profit binding | BLOCKED | 25C79 still has 716 ambiguous events. |
| rr125 raw outcome replay | NEAR EXACT | M1 OHLC replay reproduces raw `profit_r`/`exit_time` for 16871/16875 raw rows. |
| CoreB historical SOT 125 | PRESENT | 2025=104 and 2026=21 rows are available in selected top-ledger / SOT artifacts. |
| CoreA/CoreB/MEDIUM full OHLC replay | NOT DONE | Full condition-to-signal reproduction is not proven yet. |
| Feature parity | PARTIAL | 2026 feature parity is very high; 2025 remains partial. |

## A002 772 result binding remains blocked

25C79 tried to add `candidate_id`, `origin_id`, and `variant` to the A002-to-raw join.

Best key tried:

```text
entry_time + dataset + policy + candidate_id + origin_id + variant
```

Result:

```text
A002 events: 772
raw matched events: 772
profit_r + exit_time unique events: 56
ambiguous events: 716
```

Conclusion: raw candidate results exist, but the exact raw row for each A002 event is still not identified. A002 772 profit/PF/win-rate must not be computed from raw rows until this is solved.

## Raw RR125 source-context replay from OHLC

The uploaded M1 candles were used to replay `rr125_raw_signal_ledger.csv` outcomes.

Assumptions observed in replay:

```text
entry: raw ledger entry_time / entry_price
timeframe: M1
horizon: 12 hours
TP/SL: raw ledger tp_pips / sl_pips, pips-to-price factor 0.1
same-bar priority: SL first
fallback: horizon close partial R if neither TP nor SL touches
```

Replay result:

| metric | source raw ledger | OHLC replay | delta |
| --- | ---: | ---: | ---: |
| rows | 16875 | 16875 | 0 |
| matched profit_r and exit_time rows | - | 16871 | - |
| mismatch rows | - | 4 | - |
| win count | 8755 | 8755 | 0 |
| loss count | 8097 | 8097 | 0 |
| breakeven count | 23 | 23 | 0 |
| win rate | 51.8815% | 51.8815% | 0.0000 pp |
| PF | 1.273942 | 1.273403 | -0.000539 |
| total R | 2007.3035 | 2004.2035 | -3.1000 |

Dataset split:

| dataset | source WR | replay WR | source PF | replay PF | note |
| --- | ---: | ---: | ---: | ---: | --- |
| 2025 | 52.8506% | 52.8506% | 1.319540 | 1.319540 | exact on checked aggregate metrics |
| 2026 | 46.1945% | 46.1945% | 1.065871 | 1.063369 | 4 mismatches around 2026-06-02 |

Interpretation: raw source-context outcome calculation is effectively reproduced. The remaining 4 rows are source/OHLC data-version issues around 2026-06-02, not a broad replay failure.

Important: this is not CoreA/CoreB/MEDIUM strategy replay. It only verifies the raw outcome engine.

## CoreB historical SOT metrics

The 13C CoreB historical SOT/top-ledger artifacts already contain the known 125 rows.

Using `gold_v2_13c_coreb_rr125_selected_top_ledgers.csv` and its `profit` column:

| dataset | count | wins | losses | WR | PF | total R |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2025 | 104 | 75 | 29 | 72.1154% | 3.443512 | 143.0175 |
| 2026 | 21 | 17 | 4 | 80.9524% | 5.153846 | 40.5000 |
| total | 125 | 92 | 33 | 73.6000% | 3.687740 | 183.5175 |

These match the 13C report-level CoreB standalone/top-ledger metrics for WR/PF/total R.

Using `gold_v2_13c_coreb_final_sot_rows.csv` and its `profit_r` column gives slightly different total/PF because that file also carries final-SOT/component profit fields. For CoreB 13C standalone comparison, the selected top-ledger `profit` column is the clean comparison column.

## Final portfolio SOT metrics

Using `gold_v2_final_portfolio_2025_2026_sot_ledger.csv` and `profit_r`:

| dataset | count | wins | losses | breakeven | WR | PF | total R |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2025 | 346 | 239 | 103 | 4 | 69.0751% | 2.839048 | 439.5091 |
| 2026 | 183 | 132 | 44 | 7 | 72.1311% | 3.653333 | 248.7500 |
| total | 529 | 371 | 147 | 11 | 70.1323% | 3.068476 | 688.2591 |

These direct SOT-ledger metrics match the known final portfolio target level. However, OHLC condition replay for full CoreA/CoreB/MEDIUM has not yet reproduced these memberships.

## Feature parity from uploaded OHLC

CoreB refined feature parity against `coreb_refined_rule_ledgers.csv`:

| year | feature | best convention | exact rows / rows | exact ratio |
| --- | --- | --- | ---: | ---: |
| 2025 | range96 | inclusive/current-bar | 250 / 300 | 83.3333% |
| 2025 | range192 | inclusive/current-bar | 250 / 300 | 83.3333% |
| 2025 | atr14 | inclusive/current-bar | 198 / 300 | 66.0000% |
| 2025 | adx14 | rolling inclusive | 198 / 300 | 66.0000% |
| 2026 | range96 | exclusive/previous-bar | 194 / 195 | 99.4872% |
| 2026 | range192 | exclusive/previous-bar | 194 / 195 | 99.4872% |
| 2026 | atr14 | exclusive/previous-bar | 194 / 195 | 99.4872% |
| 2026 | adx14 | Wilder exclusive | 194 / 195 | 99.4872% |

Interpretation:

- 2026 OHLC feature reproduction is very close when using previous-bar / exclusive convention.
- 2025 feature reproduction is partial and likely requires source data-version or feature snapshot convention reconciliation.
- Different datasets may have used different shift conventions or source snapshots.

## Direct answer: do WR/PF match?

### 1. Raw RR125 outcome replay

Yes, almost exactly.

- WR matches exactly: 51.8815% vs 51.8815%.
- PF is nearly identical: 1.273942 source vs 1.273403 replay.
- Difference comes from 4 rows out of 16875.

### 2. CoreB historical SOT 125

Yes, when measured directly from the selected top-ledger SOT file.

- 2025: count 104, WR 72.1154%, PF 3.443512.
- 2026: count 21, WR 80.9524%, PF 5.153846.

This is a SOT ledger metric check, not an OHLC signal reproduction proof.

### 3. Final portfolio SOT

Yes, when measured directly from the final SOT ledger.

- 2025: count 346, WR 69.0751%, PF 2.839048.
- 2026: count 183, WR 72.1311%, PF 3.653333.

Again, this is direct SOT ledger measurement, not full condition replay.

### 4. CoreA/CoreB/MEDIUM OHLC condition replay

Not yet.

Full OHLC replay of CoreA/CoreB/MEDIUM signal membership has not been proven. The current result proves the raw outcome engine and partial feature parity, but not the full live evaluator.

## Required next information / next work

To continue toward real OHLC reproduction, the next audit should resolve two separate issues:

### A. A002 exact raw identity binding

Need one of the following:

```text
raw_signal_ledger row id / row index
or exact source rule key
or base_condition + added_filter_text + candidate_id + origin_id + variant + policy + entry_time
```

Purpose: reduce 716 ambiguous A002 events to 0.

### B. Formula/feature parity reconciliation

Need to map every CoreA/CoreB/MEDIUM condition field to:

```text
source field name
OHLC timeframe
rolling window
inclusive vs exclusive shift
ATR/ADX calculation convention
asof timestamp convention
```

Purpose: reproduce actual CoreA/CoreB/MEDIUM memberships from OHLC without approximate reimplementation.

## Recommended next step

`25C81_FORMULA_SOURCE_AND_FEATURE_PARITY_RECONCILIATION_AUDIT_ONLY`

Target outputs:

- formula source inventory
- required feature convention matrix
- feature parity blocker list
- A002 exact identity blocker carry-forward
- no live/final/external action
