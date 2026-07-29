RECOVERY_FF05 full-history merge
================================

Purpose
-------
The recovered historical CSVs and current MT5 CSVs have identical OHLC at identical timestamps.
This proves they use the same raw timestamp domain. No +2h or +3h conversion is applied to CSV rows.

The recovered package ends before the raw broker-server FF05 cutoff, while the current terminal files cover the cutoff.
This recovery creates a read-only union of M5, M15 and H1 history.

Safety
------
- duplicate timestamps must have exact OHLC identity;
- any overlap mismatch blocks the merge;
- CSV time remains BAR OPEN time;
- a bar is usable only at open + timeframe duration;
- raw broker-server cutoff is 2026-07-02 05:15:00;
- M5 open 05:15 is not closed at the cutoff and is excluded;
- original CSV files are not modified;
- FF05 performance is not rerun automatically.

Run
---
01_run_RECOVERY_FF05_full_history_merge.bat

Output
------
%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\RECOVERY_FF05_full_history_merge\LATEST\99_UPLOAD_PACKAGE.zip

Upload only 99_UPLOAD_PACKAGE.zip and stop.
Do not run FF05 again until the merge ZIP has been reviewed.
