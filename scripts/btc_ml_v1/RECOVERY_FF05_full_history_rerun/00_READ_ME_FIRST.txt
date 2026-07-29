RECOVERY_FF05 full-history rerun
================================

Purpose
-------
The first FF05 run was not valid because its M5/M15 inputs did not cover OOS01 and OOS02.
The exact historical package was recovered, its raw timestamp domain was proven identical to the current terminal CSVs, and a full read-only M5/M15/H1 union was created.

This recovery reruns the original frozen FF05 search without changing:

- any of the 108 preregistered cells;
- the six OOS segments;
- the bootstrap seed or 5,000 resamples;
- any survivor threshold;
- the BAR OPEN time contract;
- exact M5 entry and no future fallback;
- SL-first same-bar priority.

Input isolation
---------------
The BAT does not run FF05 against the ordinary short terminal CSVs.
It copies only the SHA-verified merged M5/M15/H1 files into an isolated temporary APPDATA terminal tree.
After FF05 completes, the generated input manifest must prove that every input path and SHA came from that isolated tree.
A mismatch invalidates the run and creates an error package.

Run
---
01_run_RECOVERY_FF05_full_history_rerun.bat

Output
------
%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\RECOVERY_FF05_full_history_rerun\LATEST\99_UPLOAD_PACKAGE.zip

The run can take several minutes. Do not start another copy.
Upload only 99_UPLOAD_PACKAGE.zip and stop.

No candidate is promoted automatically. No live, Discord, lot, or MT5 order action is enabled.
