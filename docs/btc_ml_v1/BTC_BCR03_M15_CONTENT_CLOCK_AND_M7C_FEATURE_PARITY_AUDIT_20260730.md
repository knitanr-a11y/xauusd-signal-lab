# BTC BCR03 — M15 content, clock mapping and M7C feature parity audit

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T12:42:00+09:00`
- status: `CONTENT_CLOCK_FEATURE_PARITY_ACCEPTED_ORIGINAL_ABSOLUTE_PATH_PENDING`
- outcome interpretation: not performed

## 1. Submitted candle file

User upload name:

`btcusdsharp_m15(3).csv`

The ChatGPT upload suffix `(3)` is not treated as the authoritative source filename or local path.

Content SHA256:

`b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`

Bytes: `2,110,267`

Schema:

- `time`
- `open`
- `high`
- `low`
- `close`
- `tick_volume`
- `spread`
- `real_volume`

Rows: `30,661`

Server-open range:

- earliest: `2025-09-13 08:00:00`
- latest: `2026-07-30 06:15:00`

Quality checks:

- timestamp parse failures: `0`
- duplicate server opens: `0`
- monotonic increasing: true
- normal 15-minute transitions: `30,613`
- 30-minute transitions: `45`
- 60-minute transitions: `1`
- 90-minute transitions: `1`
- explicit gap transitions: `47`
- implied missing 15-minute bars across those gaps: `53`

The gaps are retained as gaps. No interpolation is authorized.

## 2. Coverage of BCR02 BTC events

Frozen BCR02 package SHA256:

`5251428a456b7ee0a659d9ccd4b7ea2d4afde5e7e426c0b5da1ca60c5d0576b2`

BTC source events after the prospective start: `76`.

For every BTC event, with the mapping:

`MT5 server open = source bar_time_utc + 3 hours`

- expected current server-open row found: `76 / 76`
- immediately previous fully closed M15 row found: `76 / 76`
- event located at a detected CSV gap boundary: `0`
- previous closed event bar located at a detected CSV gap boundary: `0`

The event server-open range is:

- earliest: `2026-07-20 19:00:00`
- latest: `2026-07-30 04:30:00`

The submitted file therefore covers every frozen BCR02 BTC event.

## 3. UTC+3 clock evidence

Integer-hour offsets were compared descriptively using the source alert price and MT5 current-bar open.

The `+3 hour` mapping was the clear best fit:

- median absolute source-price/current-open difference: `3.88`
- mean absolute difference: `5.62`

The next closest tested integer offset was `+2 hours`:

- median absolute difference: `105.52`
- mean absolute difference: `147.47`

This is consistent with the prior M7C clock contract and supports UTC+3 for the inspected interval. It is not generalized across uninspected DST periods.

## 4. Exact M7C feature parity

The submitted candle sequence was independently used to recompute the M7C BTC features at all BTC proxy decision rows in the accepted M7C package.

BTC proxy decision rows tested: `890`.

Recomputed from the submitted CSV:

- RCI9 using the immediately previous fully closed M15 bar
- EMA20
- EMA30
- EMA40
- EMA20 minus EMA30 in basis points
- EMA30 minus EMA40 in basis points

Exact parity within floating-point precision:

- RCI9: `890 / 890`
- EMA20-minus-EMA30 bps: `890 / 890`
- EMA30-minus-EMA40 bps: `890 / 890`

Maximum absolute numerical differences:

- RCI9: `1.4210854715202004e-14`
- EMA20-minus-EMA30 bps: `3.552713678800501e-15`
- EMA30-minus-EMA40 bps: `3.552713678800501e-15`

This is strong content provenance: the submitted CSV contains the exact BTC M15 close sequence used by M7C for all inspected BTC decisions.

## 5. Source price versus MT5 price

The TradingView/VANTAGE source and MT5 are separate feeds; equality is not required.

For the 76 BTC source events:

- median absolute source-price/current-MT5-open difference: `3.88`
- mean: `5.62`
- maximum: `108.98`
- excluding raw alert ID 114: mean `4.24`, maximum `20.53`

Compared with the immediately previous MT5 close:

- median absolute difference: `3.405`
- mean: `4.98`
- excluding raw alert ID 114: mean `3.59`, maximum `11.03`

Raw alert ID 114 fired 180 seconds after its source bar boundary and carried a non-degenerate source OHLC range; its source close remained inside the corresponding MT5 current-bar range. It is retained, not treated as an error or removed.

## 6. Causal feature availability frozen by this audit

Allowed at each source decision boundary:

- all M15 bars fully closed before `current_server_open`
- current M15 `open` only
- deterministic indicators computed only from fully closed M15 bars
- gap flags and elapsed-time features that do not fill missing bars
- higher-timeframe data only after a separate as-of close-availability contract is proven

Forbidden:

- current M15 high, low or close
- later M15 bars
- interpolated gap bars
- future higher-timeframe close
- outcomes, MFE, MAE, TP/SL result or later profitability

## 7. Remaining provenance item

The file content is accepted by exact M7C feature parity, but the original local absolute path was not included in the upload.

Before BCR03 is fully closed, the user must provide the exact full path from which the submitted file was copied. No path will be guessed from filenames, modification times or prior conventions.

No additional CSV upload is required unless the stated path identifies a different file or multiple plausible candidates.

## 8. Decision

Accepted now:

- CSV content SHA and schema
- row count and time coverage
- duplicate and gap inventory
- all 76 BTC source-event mappings
- UTC+3 mapping for the inspected interval
- exact 890-row M7C RCI/EMA parity
- causal M15 feature boundary

Pending:

- original absolute source path only

No candidate formula, performance interpretation, TP/SL optimization, FF06, shadow or live action is authorized yet.
