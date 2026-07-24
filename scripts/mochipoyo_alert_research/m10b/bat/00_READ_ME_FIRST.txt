M10B GOLD multi-timeframe payoff fresh prospective shadow

CURRENT ACTION:
1) Keep genuine collector / M7C / M8C / M9V / M9Y running unchanged.
2) Run 01_initialize_fresh_runtime_once.bat ONE TIME ONLY until [M10B INIT PASS].
3) After INIT PASS, NEVER run 01 again.
4) Run 02_run_shadow_once.bat once and confirm [M10B PASS].
5) Run 05_open_latest_results.bat and submit LATEST\99_UPLOAD_PACKAGE.zip to ChatGPT.
6) Do NOT run 03_run_shadow_forever.bat until that first M10B bootstrap package is reviewed.
7) After explicit review approval, 03 is the persistent M10B loop. 04 is graceful stop for M10B only.

NEVER:
- rerun M7C/M8C/M9V/M9Y initializer
- rerun M10B BAT01 after its first INIT PASS
- reset/re-freeze/recreate any existing start
- backfill M10B by changing its start
- enable Discord, MT5 orders, live_ready or final_signal

M10B is audit-only and reads M9V v2 branch candidates READ-ONLY.
M9Y output is not an upstream dependency.
