# BTC BCR09 — pre-acceptance common-warmup incident and correction

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T19:45:00+09:00`
- status: `INITIAL_LOCAL_VALUE_OUTPUT_INVALID_CORRECTED_REPLAY_REQUIRED`

## 1. Incident

The first local BCR09 replay used a contiguous-50 warm-up for Track A immediately after the beginning of the CSV.

That replay did not reproduce the already frozen BCR06 Track A overlap-reference entry counts. It therefore cannot be accepted as a value result, regardless of its PnL.

No GitHub result, candidate decision or user-facing profitability conclusion was created from that run.

## 2. Outcome-blind correction authority

BCR06 was completed before any value outcome was opened and recorded:

- common B1/B4 eligible rows: `27,861`;
- Track A reference entries:
  - F1 LONG/SHORT: `801 / 761`;
  - F2 LONG/SHORT: `892 / 337`;
  - F3 LONG/SHORT: `412 / 400`;
  - F4 LONG/SHORT: `416 / 352`.

These counts are reproduced exactly by the following deterministic rule:

1. reserve the first `500` physical rows of the frozen M15 snapshot as the common pre-analysis warm-up;
2. begin decisions at physical row index `500` or later;
3. require the immediately preceding M15 boundary and an uninterrupted 50-bar segment;
4. do not interpolate gaps;
5. preserve active state through unavailable rows without firing an entry or exit.

Under this rule:

- B1/B4 common eligible rows equal `27,861` exactly;
- all eight Track A direction/member entry counts equal the frozen BCR06 reference exactly.

The correction is therefore selected from pre-existing outcome-blind provenance, not from PnL.

## 3. Corrected BCR09 rule

- Track A full-history replay must use the common 500-row anchor plus contiguous-50 eligibility.
- Track B uses the already accepted BCR07 episode ledger, which was generated under the same BCR06 common analysis universe.
- The exact current and previous bar requirements remain unchanged.
- All execution, spread, commission, slippage and classification rules from the BCR09 contract remain unchanged.

## 4. Exposure handling

The invalid local output has been seen by the researcher and is therefore recorded as exposed audit history. It is not a research result.

The corrected run must be reported separately with its own package hash. No threshold, signal predicate, cost assumption or classification gate may be changed after the incident.

## 5. Decision

Invalidate the first local BCR09 output. Run one corrected deterministic replay using the outcome-blind common-warmup authority above.