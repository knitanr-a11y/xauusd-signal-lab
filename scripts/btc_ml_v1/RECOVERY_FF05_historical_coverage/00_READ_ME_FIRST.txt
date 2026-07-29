RECOVERY_FF05 historical coverage
=================================

Purpose
-------
The submitted FF05 run used terminal CSVs whose M5/M15 history starts in September 2025.
Therefore OOS01 and OOS02 had no raw M5/M15 coverage and OOS03 was only partial.
The result cannot be finalized as a formal NO_CANDIDATE.

This recovery searches the likely local folders for:

- BTCUSD_HISTORY_CHAT_PACKAGE*.zip
- exact frozen btcusdsharp_m5.csv
- exact frozen btcusdsharp_m15.csv
- exact frozen btcusdsharp_h1.csv
- exact frozen btcusdsharp_d1.csv

Every candidate is checked by SHA256 against the frozen July 2 reproduction reference.
Source files are read-only. The FF05 performance search is not rerun automatically.

Run
---
01_run_RECOVERY_FF05.bat

Output
------
%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\RECOVERY_FF05_historical_coverage\LATEST\99_UPLOAD_PACKAGE.zip

Upload only 99_UPLOAD_PACKAGE.zip and stop.

Do not run FF05 again until the recovery ZIP has been reviewed.
