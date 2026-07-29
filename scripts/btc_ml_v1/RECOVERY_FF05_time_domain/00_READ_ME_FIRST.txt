RECOVERY_FF05 time-domain audit
===============================

Purpose
-------
The exact frozen historical BTC package has been recovered.
Before rerunning FF05, this audit determines whether its CSV time column is UTC bar-open time or raw MT5 broker-server bar-open time.

Method
------
For M5, M15, and H1, the restored reference OHLC is compared with current terminal OHLC at timestamp shifts from -5 through +5 hours.

The expected proof pattern is:

- restored reference +2 hours matches current terminal during broker winter time;
- restored reference +3 hours matches current terminal during broker summer time;
- shift 0 does not match materially.

This demonstrates that the restored package is UTC bar-open time while the current terminal files are raw broker-server bar-open time with DST.

The audit also enforces:

- CSV time means BAR OPEN time;
- a bar is usable only at time + exact timeframe duration;
- the M5 bar opening exactly at the 2026-07-02 02:15 UTC cutoff is not closed yet and must be excluded;
- source CSV files are read-only;
- FF05 performance is not rerun.

Run
---
01_run_RECOVERY_FF05_time_domain.bat

Output
------
%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\RECOVERY_FF05_time_domain\LATEST\99_UPLOAD_PACKAGE.zip

Upload only 99_UPLOAD_PACKAGE.zip and stop.
Do not rerun FF05 until this ZIP has been reviewed.
