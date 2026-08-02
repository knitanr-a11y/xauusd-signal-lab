# GOLD SCALP ACTIVATION / RETEST V1 — Reproduction Note

## Inputs

Use the existing GOLD candle CSVs already authorized for the isolated retrospective research:

- M1 is required for setup reference, activation, retest, confirmation, next-open entry and exact outcome resolution.
- M5 is used by the pre-existing structural-event cache.
- H1/H4 regime values are inherited only from that causal cache.

Do not use V19 or Challenger C1 runtime scores, ranks, trades, state or Discord outputs as candidate inputs.

## Scripts in the result package

Run in this order:

1. `gold_scalp_activation_retest_v1.py`
   - creates 138 activation/retest contracts from 170,664 setup rows;
   - writes approximately 4.18 million entry rows and exact outcomes.
2. `compact_activation_ledger.py`
   - converts the large string ledger to numeric NumPy arrays.
3. `analyze_activation_retest_compact.py`
   - performs sequential half-year exit freezing, calibration selection, target evaluation, overlap removal and promotion diagnostics.
4. `gold_scalp_activation_retest_quality_v1b.py`
   - tests causal quality layers on the recurring VOLUME_ABSORPTION SHORT family.
5. `gold_scalp_activation_retest_partial_exit_v1c.py`
   - adds staged exits alongside the original exits.
6. `gold_scalp_activation_retest_partial_only_v1d.py`
   - restricts the rerun to staged exits only.
7. `gold_scalp_activation_retest_partial_stack_v1e.py`
   - applies the same P50 TP5/TP10 SL5 exit to all 3,864 components as a universality check.

## Execution contract

- MT5 broker-server naive time.
- Closed rows only.
- Setup event decision is causal.
- Activation/retest information is intentionally observed after setup and before entry.
- Entry is always the next contiguous M1 open after confirmation.
- Entry spread gate is at most 30 recorded points.
- Standard spread is 0.30 USD once.
- Protective stop is checked first when adverse and favorable prices are both reachable in one M1.
- One-position non-overlap is applied chronologically.

## Partial-exit accounting

For `P50_TP5_TP10_SL5_H240`:

- initial full-position SL is -5 USD;
- first TP is +5 USD on 50% of the position;
- after first TP, the remaining 50% stop moves to breakeven;
- final TP is +10 USD on the remaining 50%;
- full final-target result is +7.5 USD;
- first TP followed by breakeven is +2.5 USD;
- same-M1 initial protective stop has priority;
- after first TP, a same-M1 breakeven touch conservatively records only the realized partial profit.

## Audit boundaries

The provisional family is retrospective and observation-only. Do not backfill it into a claimed untouched validation, interpolate activation/retest thresholds, delete the 2025H1 loss, or restore only winning subperiods.
