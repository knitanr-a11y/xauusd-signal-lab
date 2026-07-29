BTC FF05 candidate rebuild search
=================================

Purpose
-------
Evaluate exactly 108 preregistered causal M15 trend-impulse research cells.

Time contract
-------------
- CSV time is BAR OPEN time.
- M15 OHLC becomes known at time + 15 minutes.
- Entry requires the exact M5 open at that decision time.
- Missing exact M5 means NO_TRADE.
- H1 must already be closed by the signal M15 OPEN.
- Exit M5 high/low is known at M5 time + 5 minutes.
- Same-M5 SL and TP contact uses SL first.

Outcome isolation
-----------------
- Data after 2026-07-02 02:15:00 UTC is excluded from design and ranking.
- The six FF02 losses are not used to create or change conditions.
- All 108 cells and rejected cells are preserved.

Run
---
Run once:

01_run_FF05.bat

The run can take several minutes. Do not start a second copy.

Output
------
The BAT opens:

%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\FF05_candidate_rebuild_search\LATEST\99_UPLOAD_PACKAGE.zip

Upload only that ZIP and stop.

Safety
------
Research-only. No promotion, lot design, live use, Discord, MT5 order, GOLD, or MOCHIPOYO action.
