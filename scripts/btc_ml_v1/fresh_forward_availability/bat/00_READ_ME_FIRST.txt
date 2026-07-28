BTC ML V1 / Stage 01 fresh-forward availability audit
=======================================================

Purpose
-------
This folder contains only the user-facing BAT files for the BTC4/BTC5/BTC6/BTC7R/BTC9R fresh data availability audit.
The internal Python implementation is kept separately under the sibling python folder.

Important input distinction
---------------------------
- Current fresh-forward readiness is decided from post-cutoff M5/M15/H1/D1/H4 data.
- BTC4 current readiness requires post-cutoff H4 and M5 data.
- The old 2017-start H4 file belonged to BTCUSD_H4_WARMUP_PACKAGE.zip and was used only for exact historical BTC4 stacking reproduction.
- That old package is optional in Stage 01. Its absence does not block current fresh-forward readiness and the user does not need to create C:\BTC_REPRO manually.

Run order
---------
1. Pull the latest feature/mochipoyo-alert-research branch in GitHub Desktop.
2. Run 01_run_availability_audit.bat once.
3. The BAT verifies that all four output files are present, non-empty, the JSON is readable, and the ZIP is valid.
4. Only after that verification succeeds, Explorer opens with 99_UPLOAD_PACKAGE.zip selected.
5. Upload only that selected 99_UPLOAD_PACKAGE.zip to ChatGPT.
6. 02_open_latest_results.bat is only for reopening and re-verifying the same package later.

Success display
---------------
[BTC_ML_V1_01] SUCCESS: availability audit complete and all four output files were verified.

The command window shows a real disk file listing and remains open after success until a key is pressed.
It must not disappear immediately after opening Explorer.

Error behavior
--------------
- An empty LATEST directory is never treated as success.
- On BLOCKED, FAILED, missing output, zero-byte output, invalid JSON, invalid ZIP, or missing LATEST, Explorer is not opened as success.
- The command window pauses and remains visible so the error can be copied or photographed.
- A persistent console log is kept at:
  %LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability\last_run_console.log
- Do not run any evaluator after an error.

Do not run simultaneously
-------------------------
Run only one copy of 01 at a time. 02 only re-verifies and opens the result package and may be used after 01 finishes.

Output location
---------------
%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability\
  last_run_console.log
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
