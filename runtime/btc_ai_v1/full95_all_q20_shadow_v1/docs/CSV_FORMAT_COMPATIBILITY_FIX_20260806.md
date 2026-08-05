# CSV format compatibility fix — 2026-08-06

Before user-PC activation, the Full95 Shadow loader was found to be fixed to semicolon-delimited CSVs. The existing `btcusdsharp_*.csv` exporter contract uses comma-delimited files with header `time,open,high,low,close,...`.

This compatibility correction changes only CSV parsing:

- auto-detect comma, semicolon, or tab delimiter from the header;
- normalize UTF-8 BOM, whitespace, angle-bracket MT5 headers, and column case;
- accept full `time` timestamps and MT5 `<DATE>` plus `<TIME>` pairs;
- require the same canonical OHLC fields and fail closed with a detected-column diagnostic.

The model, 95 features, Q20 threshold, parent rule, activation policy, review gates, and Stage55 remain unchanged. The prior failed initialization aborted before activation, so no activation cutoff or prospective ledger was created.

## User-PC commands after pulling this commit

Use `launchers/02_INIT_ONCE_CSV_COMPAT.bat` for the one-time activation. After activation, use `launchers/03_PROCESS_CSV_COMPAT.bat` for continued processing. The original `02_INIT_ONCE.bat` and `03_PROCESS.bat` remain preserved as frozen historical launchers.
