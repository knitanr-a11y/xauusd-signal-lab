M10W26 MMO1 causal-NEITHER fresh prospective shadow — AUDIT ONLY

Keep collector, M7C, M8C, M9V, M9Y, M10B, M10E, M10P, M10P2 and M10W19 running unchanged.

Order for the first launch only:
1. Run 01_initialize_fresh_start_once.bat exactly once.
2. After INIT PASS, run 03_run_shadow_forever.bat and keep its window open.
3. Use 04_stop_shadow_forever.bat for a normal stop.
4. After initialization, never rerun BAT01. Restart only with BAT03.

02_run_shadow_once.bat is a read/rebuild audit helper and is not the persistent operator.

M10W26 is independent from all existing runtimes and starts. It does not send Discord messages, place MT5 orders, enable a live gate, modify M10W19, or backfill pre-start candidates.

Never delete or edit the M10W26 runtime manifest, state, lock, STOP file, private snapshot or adapter journal manually.
