BTC ML V1 / Stage 01 fresh-forward availability audit
=======================================================

Purpose
-------
This folder contains only the user-facing BAT files for the BTC4/BTC5/BTC6/BTC7R/BTC9R fresh data availability audit.
The internal Python implementation is kept separately under the sibling python folder.

Run order
---------
1. Run 01_run_availability_audit.bat once.
2. Success display:
   [BTC_ML_V1_01] SUCCESS: availability audit complete.
3. On BLOCKED or FAILED, stop and check the LATEST report. Do not run any evaluator.
4. Run 02_open_latest_results.bat to open the newest result folder.
5. Upload only 99_UPLOAD_PACKAGE.zip from LATEST to ChatGPT.

Do not run simultaneously
-------------------------
Run only one copy of 01 at a time. 02 only opens the result folder and may be used after 01 finishes.

Output location
---------------
%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability\
  LATEST\
    00_READ_ME_FIRST.txt
    01_availability_summary.json
    02_availability_report.txt
    99_UPLOAD_PACKAGE.zip
  archive\
    <UTC execution timestamp>\

Safety
------
Availability audit only. CSV files are read-only.
No candidate engine, performance evaluator, reproduction, collector, Mochipoyo runtime, GOLD runtime, Discord, MT5 order, live-ready or final-signal action is executed.
