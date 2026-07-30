# BTC BCR03 — source-to-MT5 candle mapping and feature availability contract

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30`
- status: `SOURCE_CANDLE_EVIDENCE_PENDING`
- outcome interpretation: forbidden

## 1. Purpose

Map the BCR02 BTC source event ledger to the exact BTC M15 candle source that will be used for research.

The purpose is not to measure wins or losses. It is to establish the causal input available at each source alert decision boundary.

## 2. Frozen event input

- BCR01 source package SHA256: `bc562948ee8baefba32d0e291a54341243da4684bdbf43d652676d5fcdab5611`
- BCR02 ledger package SHA256: `5251428a456b7ee0a659d9ccd4b7ea2d4afde5e7e426c0b5da1ca60c5d0576b2`
- prospective start: `2026-07-20T14:54:15Z`
- BTC raw event rows after start: `76`
- BTC M7C-v1 supported source events: `53`

## 3. Required candle evidence

The exact BTC M15 CSV used for mapping must be supplied with:

- original filename
- original absolute path
- file SHA256
- byte size
- header/schema
- row count
- earliest and latest server-open time
- duplicate server-open count
- timestamp monotonicity
- explicit timezone/clock-domain evidence

No similar filename, old snapshot or automatic fallback may be substituted.

## 4. Mapping checks

For every BTC source event:

1. Treat `bar_time_utc` as the source decision boundary.
2. Test the frozen observed mapping `MT5 server time = UTC + 3 hours` for this interval.
3. Match the corresponding MT5 `current_server_open`.
4. Identify the immediately previous fully closed M15 bar.
5. Allow current-bar open only.
6. Forbid current-bar high, low and close.
7. Record missing/gap/duplicate bars explicitly.
8. Compare source OHLC/price to MT5 values descriptively; do not force equality across feeds.

## 5. Feature availability

BCR03 must produce an allowlist of features computable from:

- all M15 bars fully closed before decision time
- current M15 open
- frozen higher-timeframe bars only when their close was available by decision time

Forbidden:

- current M15 high/low/close
- later M15 bars
- future HTF close
- trade outcome fields
- MFE/MAE
- TP/SL result
- any feature selected because of later profitability

## 6. Initial evidence request

The next evidence is the exact `btcusdsharp_m15.csv` currently used for the BTC/M7C environment, copied without stopping or editing M7C/Collector.

Place that one file in a ZIP and preserve the original filename. Do not send unrelated GOLD CSVs.

If more than one file with that name exists, do not choose by modification time alone. Provide the full paths of the candidates first so the authoritative source can be resolved explicitly.

## 7. Stop conditions

Stop before mapping if:

- the exact source path cannot be established;
- more than one plausible file exists;
- the file lacks the July 2026 event interval;
- timestamp interpretation is ambiguous;
- current-bar high/low/close would be required;
- a gap is silently interpolated;
- outcomes would need to be opened.
