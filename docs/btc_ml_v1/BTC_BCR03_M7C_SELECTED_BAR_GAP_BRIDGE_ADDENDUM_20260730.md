# BTC BCR03 addendum — M7C selected bar versus exact previous M15 bar

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T13:46:00+09:00`
- outcome interpretation: not performed
- candidate formula: not designed

## 1. Why this addendum exists

BCR03 established that the submitted BTC M15 CSV reproduces the M7C BTC RCI9 and EMA-spread values for all 890 inspected proxy decisions.

BCR04 then represented every theoretical 15-minute decision boundary, including missing-bar boundaries. This exposed one distinction that the original BCR03 wording did not state clearly:

- `M7C selected-bar content parity`: 890 / 890;
- `exact immediately-previous M15 boundary parity`: 889 / 889 eligible rows;
- one M7C row used the latest available observed bar across a 30-minute gap.

The content-provenance conclusion remains valid. The exact-previous-bar availability claim is narrowed for one control row.

## 2. Exact gap row

- decision time UTC: `2026-07-25T07:30:00Z`
- current MT5 server open: `2026-07-25 10:30:00`
- expected exact previous M15 open: `2026-07-25 10:15:00`
- exact previous row present: `false`
- M7C selected server open: `2026-07-25 10:00:00`
- selected lag: `30 minutes`
- BCR04 class: `IDLE_NON_EVENT_CONTROL`
- source event on row: none

The immediately preceding theoretical decision boundary, `2026-07-25T07:15:00Z`, had no current `10:15` candle row.

## 3. Correct interpretation

### Content provenance

The M15 content still reproduces M7C using M7C's recorded `selected_server_open`:

- RCI9: 890 / 890;
- EMA20-minus-EMA30 bps: 890 / 890;
- EMA30-minus-EMA40 bps: 890 / 890.

### BCR04 causal universe

BCR04 does not copy the M7C gap bridge into the research-control universe.

- the missing `10:15` current-bar row is retained and marked ineligible;
- the `10:30` row is retained but its exact previous bar is marked missing;
- no nearest, last-available, next, or interpolated fallback is used;
- both rows remain visible in the ledger;
- no BTC source event occurs on either row.

Therefore BCR04 has 907 theoretical rows, 905 core-feature-eligible rows, and two explicit gap-adjacent rows.

## 4. Impact

This is not:

- a source-data corruption;
- an M7C state mismatch;
- a profitability result;
- a candidate failure.

It is a timing-availability nuance. Future Track A fidelity work must distinguish:

1. exact previous M15 boundary features; and
2. M7C last-observed selected-bar behavior across a missing boundary.

The BTC research candidate will remain fail-closed on an absent exact previous bar unless a separate gap policy is preregistered before outcome evaluation.
