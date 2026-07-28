M10W34 SNDX1 low-ATR causal-NEITHER fresh prospective shadow — AUDIT ONLY

Keep collector, M7C, M8C, M9V, M9Y, M10B, M10E, M10P, M10P2, M10W19 and M10W26 running unchanged.

First launch only:
1. Run 01_initialize_fresh_start_once.bat exactly once.
2. Require PRESTART ENGINE PASS and INIT PASS.
3. Run 03_run_shadow_forever.bat and keep its window open.
4. After first M10W34 PASS, run 05_audit_initial_health.bat and upload its ZIP.

After initialization, never rerun BAT01. Restart only with BAT03 after an actual stop or reviewed incident.
Use BAT04 for a normal STOP-file shutdown.

M10W34 is independent, audit-only, Discord OFF, MT5 order OFF, live/final gate OFF, no historical backfill, exact M1 entry/exit, fixed 240-minute horizon and one-position semantics.
