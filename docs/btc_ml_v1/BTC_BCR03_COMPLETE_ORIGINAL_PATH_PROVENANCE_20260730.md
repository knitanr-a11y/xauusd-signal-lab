# BTC BCR03 — original path provenance complete

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T13:12:00+09:00`
- status: `BCR03_COMPLETE_SOURCE_CANDLE_PROVENANCE_FROZEN`
- outcome interpretation: not performed

## 1. Exact original source path

The user supplied the exact Windows path from which the audited BTC M15 CSV was copied:

`C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv`

This path is recorded verbatim as `USER_ATTESTED_ORIGINAL_ABSOLUTE_PATH`.

It was not guessed from the uploaded filename, modification time, MetaQuotes conventions, or a similar file. The ChatGPT upload suffix in `btcusdsharp_m15(3).csv` is not part of the authoritative local filename.

The remote assistant cannot independently stat the user's Windows path. Path authority therefore consists of:

1. the user's exact path attestation; and
2. the already accepted content-provenance proof described below.

## 2. Content identity frozen with the path

- original filename: `btcusdsharp_m15.csv`
- content SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- bytes: `2,110,267`
- rows: `30,661`
- server-open range: `2025-09-13 08:00:00` through `2026-07-30 06:15:00`
- duplicate server opens: `0`
- gap transitions: `47`
- implied missing M15 bars: `53`

The exact path must not be separated from this content SHA when the BCR03 source is referenced.

## 3. Provenance evidence

The submitted content was independently checked against the accepted M7C decision evidence:

- BTC proxy decision rows: `890`
- RCI9 parity: `890 / 890`
- EMA20-minus-EMA30 bps parity: `890 / 890`
- EMA30-minus-EMA40 bps parity: `890 / 890`

The content therefore contains the exact M15 close sequence used by M7C for every inspected BTC decision.

For the BCR02 BTC source-event ledger:

- BTC source events: `76`
- current server-open rows found with UTC+3 mapping: `76 / 76`
- immediately previous fully closed bars found: `76 / 76`
- event rows on detected gap boundaries: `0`

## 4. Frozen causal boundary

Allowed at a decision boundary:

- all M15 bars fully closed before the current server-open;
- current M15 open only;
- deterministic features computed only from fully closed bars;
- explicit gap and elapsed-time indicators without filling missing bars.

Forbidden:

- current M15 high, low or close;
- later M15 bars;
- interpolated bars;
- unproven higher-timeframe close availability;
- outcomes, MFE, MAE, TP/SL results, or later profitability.

## 5. Decision

BCR03 is complete.

The authoritative BCR03 candle source is the exact tuple:

- path: `C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv`
- SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`

A future file at the same path is not automatically the same frozen source. Its SHA must be checked. A file with the same SHA at another path is a content-identical copy but does not silently replace the recorded origin path.

No candidate formula, profitability conclusion, TP/SL optimization, FF06, shadow, Discord, or MT5 order is authorized by BCR03 completion alone.
