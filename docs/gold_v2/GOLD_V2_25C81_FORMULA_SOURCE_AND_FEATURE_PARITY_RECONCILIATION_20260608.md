# GOLD V2 25C81 Formula source and feature parity reconciliation

Created UTC: 2026-06-08T07:52:08.286862+00:00

Status: `FORMULA_FEATURE_RECONCILIATION_READY_AUDIT_ONLY_BLOCKERS_IDENTIFIED`

## Scope

This is an audit-only reconciliation document. It summarizes which formula sources are executable, which feature fields are required, which outcome/PF checks already match, and what still blocks OHLC-based CoreA/CoreB/MEDIUM reproduction.

No source recovery, live evaluator, final signal, Discord, MT5, or AI action is approved.

## Key conclusion

The raw RR125 outcome engine is almost fully reproducible from OHLC, and SOT metric aggregation matches the known CoreB/final SOT ledgers. However, full CoreA/CoreB/MEDIUM OHLC signal replay is **not yet proven**.

The two hard blockers are:

1. A002 772 result binding remains ambiguous: 716 events still cannot be bound to one raw row.
2. Raw/CoreB feature formula parity is not complete: 38 raw rule features are required, including many M5 and ATR-normalized fields that were not fully checked in 25C80.

## What is already reliable

### SOT metric aggregation

CoreB selected top-ledger metrics aggregate as:

| dataset | count | wins | losses | breakeven | win_rate | pf | total_r |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2025 | 104 | 75 | 29 | 0 | 0.721154 | 3.44351 | 143.017 |
| 2026 | 21 | 17 | 4 | 0 | 0.809524 | 5.15385 | 40.5 |
| total | 125 | 92 | 33 | 0 | 0.736 | 3.68774 | 183.517 |

Final portfolio SOT metrics aggregate as:

| dataset | count | wins | losses | breakeven | win_rate | pf | total_r |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2025 | 346 | 239 | 103 | 4 | 0.690751 | 2.83905 | 439.509 |
| 2026 | 183 | 132 | 44 | 7 | 0.721311 | 3.65333 | 248.75 |
| total | 529 | 371 | 147 | 11 | 0.701323 | 3.06848 | 688.259 |

These are direct SOT-ledger checks, not OHLC membership reproduction.

### Raw RR125 outcome replay

25C80 showed that M1 OHLC first-touch replay reproduced `rr125_raw_signal_ledger.csv` profit/exit for 16871 of 16875 rows. WR matched exactly; PF delta was about -0.000539. This validates the raw outcome engine, not A002 membership.

## Formula source inventory

| source | role | rows | executable_formula_text | outcome_columns | condition_rows | feature_role | replay_status | limitation |
| --- | --- | ---: | --- | --- | ---: | --- | --- | --- |
| rr125_raw_signal_ledger.csv | RR125 raw candidate/source-context ledger | 16875 | YES: base_condition + added_filter_text | profit_r / exit_time | 33 | raw CoreB source rules | OUTCOME_REPLAY_NEAR_EXACT | A002 exact row binding blocked by 25C79 |
| rr125_top_ledgers.csv | RR125 cluster/top-ledger summary | 2811 | NO_OR_PARTIAL | | | | | cluster summary; not row-level membership; no base/added formula text |
| gold_v2_13c_coreb_rr125_selected_top_ledgers.csv | CoreB historical SOT selected top-ledger 125 | 125 | NO_OR_PARTIAL | | | | | historical SOT subset; not A002 772 full result ledger |
| gold_v2_coreb_combined_evaluator_replay_rows.csv | candidate formula replay output | 30273 | NO_OR_PARTIAL | | | | | hit counts only; 7 candidate rows vs expected 125, parity not proven |
| coreb_refined_rule_ledgers.csv | CoreA/CoreB/MEDIUM refined/source ledger with feature snapshot | 495 | NO_OR_PARTIAL | | | | | contains feature values and result rows, but not full executable formula source for every component |
| gold_v2_final_portfolio_2025_2026_sot_ledger.csv | final portfolio SOT ledger | 529 | NO_OR_PARTIAL | | | | | membership/performance SOT, not complete OHLC formula source |
| gold_v2_new_search_summary.json | new OHLC search audit | json | NO_OR_PARTIAL | | | | | invalid as strategy source; in-sample overfit, WF failed |

## Raw condition inventory

Parsed from `rr125_raw_signal_ledger.csv`:

- unique raw rule keys: 33
- unique parsed condition rows: 49
- required feature fields: 38

The full condition table is in `04_25c81_raw_condition_inventory.csv`.

## Required feature matrix

The raw rule features include M15 and M5 fields, ATR-normalized distances/returns/ranges, Donchian position, EMA slope, compression ranges, and candle wick fields.

Feature parity status is summarized in `05_25c81_required_feature_matrix.csv`.

Important interpretation:

- 25C80 checked only a subset/proxy of these fields (`range96`, `ret96`, `atr14`, `tr_mean_32`, `adx14`, `trend_eff96`).
- Many actual raw rule fields, such as `m5_*`, `donch_pos_*`, `dist_low_*_atr`, `dist_high_*_atr`, `ema*_slope_*_atr`, and `compression_range_*`, still need explicit formula parity tests.

## Blockers

| blocker_id | component | status | evidence | needed |
| --- | --- | --- | --- | --- |
| 25C81-B001 | A002_RESULT_BINDING | BLOCKED | 25C79: 716 ambiguous events after entry_time/dataset/policy/candidate_id/origin_id/variant join | raw row id or base_condition+added_filter_text exact mapping for each A002 event |
| 25C81-B002 | RAW_CONDITION_FEATURE_PARITY | NOT_PROVEN | 38 raw rule feature fields parsed; 25C80 only checked proxy M15 features and not m5/donch/ema/dist/compression formulas | field-by-field OHLC formula definitions and parity tests |
| 25C81-B003 | COREB_COMBINED_REPLAY | NOT_PROVEN | 13C/combined replay: candidate formula produced 7 rows vs expected 125 | source-validated same_count cluster universe and selected rule replay |
| 25C81-B004 | COREA_MEDIUM_FORMULAS | PARTIAL_SOURCE_ONLY | SOT memberships and feature snapshots exist; complete executable OHLC formula source not established | component formula inventory and feature convention matrix |
| 25C81-B005 | 2025_FEATURE_PARITY | PARTIAL | 25C80: 2025 feature exact ratios roughly 62%-83% depending on feature | data-version/source-snapshot/shift reconciliation |
| 25C81-B006 | EXTERNAL_ACTIONS | OFF | audit-only guardrails | explicit future approval after parity gates |

## Readiness

| gate | status | detail |
| --- | --- | --- |
| SOT_METRIC_AGGREGATION | READY | CoreB selected top-ledger and final portfolio SOT metrics aggregate correctly |
| RAW_OUTCOME_ENGINE_REPLAY | NEAR_EXACT | 25C80 reproduced 16871/16875 raw rows; WR exact and PF delta small |
| A002_772_RESULT_USE | BLOCKED | 25C79 ambiguity remains; no all-772 profit/PF allowed |
| COREB_OHLC_SIGNAL_REPLAY | BLOCKED | feature parity and same_count source cluster parity not proven |
| COREA_MEDIUM_OHLC_SIGNAL_REPLAY | NOT_READY | full executable formulas need inventory and parity checks |
| LIVE_FINAL_SIGNAL | OFF | no external action allowed |

## Next step

Recommended next step: `25C82_FIELD_FORMULA_IMPLEMENTATION_AUDIT_ONLY`

Purpose:

- implement only deterministic feature calculations required by raw/CoreB rules;
- compare each calculated field against existing source snapshots where available;
- do not use the result as final signal;
- do not treat mismatching formulas as source-of-truth.

If 25C82 succeeds, later steps can attempt raw 33-rule replay and same-count cluster reproduction.
