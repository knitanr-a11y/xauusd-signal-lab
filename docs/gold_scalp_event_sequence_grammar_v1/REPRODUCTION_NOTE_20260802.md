# GOLD SCALP EVENT-SEQUENCE GRAMMAR V1 — Reproduction Note

Date: 2026-08-02

## Required inputs

Use the same local candle union used by the preceding scalp research:

- `gold_v3_2023_2026_m1(3).csv` plus `goldsharp_m1(3).csv`;
- `gold_v3_2023_2026_m5(3).csv` plus `goldsharp_m5(3).csv`;
- H1 and H4 unions for the raw HTF grammar;
- `all_candidates_with_outcomes.pkl` from the regime-stack research for existing-event sequence construction.

Duplicate timestamps are resolved by keeping the later-listed source. Do not convert timestamps to JST.

## Local scripts

The result package contains:

- `gold_scalp_event_sequence_grammar_v1.py`;
- `gold_scalp_event_sequence_grammar_v1b.py`;
- `gold_scalp_event_sequence_timing_v1.py`;
- `analyze_event_sequence_timing_v1_fast.py`;
- `gold_scalp_raw_m5_grammar_v1.py`;
- `gold_scalp_grammar_promotion_v1.py`.

## Run order

1. Run ordered existing-event grammar V1.
2. Run causal strength/dwell V1B.
3. Run timing simulation; if the full analysis exceeds the execution budget, use the saved timing ledger and the fast analysis script without changing any condition.
4. Run the raw-M5 finite-state grammar study.
5. Run unified pseudo-forward grammar promotion.

Compute-only amendments must not alter events, grammar definitions, sides, exits, periods, thresholds or gates.

## Execution invariants

- entry at the next available exact M1 open after a completed grammar;
- spread 0.30 USD once;
- recorded entry spread gate at 30 points;
- same-M1 collision uses the protective stop first;
- exact horizon and continuity required;
- one-position non-overlap;
- no outcome-based threshold interpolation;
- no deletion of losing months, blocks, sides or grammar families.

## Expected consolidated results

- ordered-event sequence candidates: 40,766, calibration passes zero;
- strength/dwell CORE: 169 trades, PF about 0.701;
- timing CATALOG: 49 trades, PF about 0.974;
- raw-M5 BALANCED: 214 trades, PF about 0.595;
- promotion paper observations: 22;
- promoted eligible components: zero.

The formal result must remain `NO_FORMAL_CANDIDATE` unless a separately preregistered study produces new evidence.
