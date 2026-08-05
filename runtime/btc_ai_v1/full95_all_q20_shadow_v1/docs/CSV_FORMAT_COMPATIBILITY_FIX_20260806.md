# CSV format compatibility fix — 2026-08-06

Before user-PC activation, the Full95 Shadow loader was found to be fixed to semicolon-delimited CSVs. The existing `btcusdsharp_*.csv` exporter contract uses comma-delimited files with header `time,open,high,low,close,...`.

This compatibility correction changes only CSV parsing:

- auto-detect comma, semicolon, or tab delimiter from the header;
- normalize UTF-8 BOM, whitespace, angle-bracket MT5 headers, and column case;
- accept full `time` timestamps and MT5 `<DATE>` plus `<TIME>` pairs;
- require the same canonical OHLC fields and fail closed with a detected-column diagnostic.

The model, 95 features, Q20 threshold, parent rule, activation policy, review gates, and Stage55 remain unchanged.

## User-PC launchers

- one-time activation: `launchers/02_INIT_ONCE_CSV_COMPAT.bat`;
- continuous observation: `launchers/03_PROCESS_CSV_COMPAT.bat`;
- status: `launchers/04_STATUS.bat`.

`03_PROCESS_CSV_COMPAT.bat` is a 60-second continuous loop. Its window title is:

`BTC AI V1 Full95 Q20 Shadow - ACTIVE OBSERVATION LOOP`

It continues after normal cycles and stops without automatic retry when the process command returns an error. Closing the window stops only the Full95 Q20 Shadow; Stage55 remains separate.

The formal activation completed at `2026-08-05 20:00:00` MT5 broker time. Do not rerun the one-time activation launcher.
