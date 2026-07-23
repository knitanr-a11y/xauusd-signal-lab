M9F DIVERGENCE RECENCY / LOCALITY AUDIT
=======================================

Purpose
-------
M9E correctly used only causally confirmed pivots, but pooling M1/M5/M15/H1/H4 x five oscillators x two pivot scales made ANY-divergence saturated.
M9F does NOT discard regular or hidden divergence. It separates:

1) divergence freshness, normalized in bars of its own timeframe
   - <=2 bars
   - <=3 bars
   - <=5 bars
   - <=10 bars
   These are observation grids only, NOT trading thresholds.

2) relation to the current proxy trade
   - both pivots formed after the original signal
   - only the second pivot formed after the original signal
   - both pivots pre-date the signal

Regular / hidden, supportive / opposing, RCI9/14/18, MACD line/histogram, timeframe and pivot scale remain separate.

How to run
----------
1. Keep M8C, M7C and collector running. Do NOT reset any prospective start.
2. Run exactly once:
   01_run_divergence_recency_locality_audit.bat
3. Success shows:
   [M9F PASS]
4. On success run:
   02_open_latest_results.bat
5. Submit only:
   %LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9F\LATEST\99_UPLOAD_PACKAGE.zip

If BLOCKED
----------
Do not repeat the BAT unchanged. Send the full screen output to ChatGPT.

Research status
---------------
- audit-only
- Tier B proxy replay is NOT genuine Mochipoyo source truth
- same-sample rule/gate promotion is forbidden
- no Discord send
- no MT5 order
- no live-ready/final-signal/entry gate
- M7C formula and thresholds unchanged
- M8C unchanged and still prospective
