M10E H1 COMPOUND-LOSS FILTER FRESH PROSPECTIVE SHADOW

AUDIT ONLY.
Keep collector / M7C / M8C / M9V / M9Y / M10B unchanged.
M10E uses a new independent fresh MT5-server-time start.
It compares the unchanged H1 runner50 baseline against the fixed M10D compound-loss filter.
No historical backfill. No Discord. No MT5 orders. No live promotion.

ORDER:
1. Run 01_initialize_fresh_runtime_once.bat exactly once until [M10E INIT PASS].
2. After INIT PASS, NEVER run BAT01 again and never delete/recreate the M10E runtime/start.
3. Run 02_run_shadow_once.bat once.
4. After [M10E PASS], run 05_open_latest_results.bat and submit only 99_UPLOAD_PACKAGE.zip to ChatGPT.
5. DO NOT run 03_run_shadow_forever.bat until the bootstrap package has been reviewed.

If BAT01 or BAT02 is BLOCKED, do not reset anything. Send the full console output.
