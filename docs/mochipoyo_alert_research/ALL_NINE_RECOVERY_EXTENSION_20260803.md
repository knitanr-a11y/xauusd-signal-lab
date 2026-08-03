# MOCHIPOYO all-nine recovery extension

Date: 2026-08-03  
Repository: `knitanr-a11y/xauusd-signal-lab`  
Implementation branch: `agent/mochipoyo-all-nine-recovery`  
Target branch: `feature/mochipoyo-alert-research`

## Purpose

The original recovery operators covered the seven bounded-adapter loops through M10W19. M10W26 and M10W34 were initialized later and have independent private-snapshot runtimes, locks, status files and BAT03 launchers.

This addendum extends the recovery surface to all nine forward loops without modifying any strategy, formula, threshold, horizon, causal coverage rule, frozen runtime or prospective start.

The nine forward loops are:

- M9V
- M9Y
- M10B
- M10E
- M10P
- M10P2
- M10W19
- M10W26
- M10W34

## Operators

### Genuine forced Windows/PC reboot only

`scripts/mochipoyo_alert_research/recovery/bat/01_recover_after_forced_reboot.bat`

The operator now checks collector, M7C and all nine forward-loop process markers before touching a lock. It then verifies the nine immutable runtime starts. Only after every precheck passes does it archive every existing lock and then remove stale locks.

It does not reset or delete runtime manifests, starts, state/history, SQLite, bounded journals, private snapshots or MT5 CSVs.

Do not run BAT01 merely as a test.

### Unexplained stopped loop

`scripts/mochipoyo_alert_research/recovery/bat/02_audit_stopped_fresh_loops.bat`

This remains read-only and now includes M10W26 and M10W34 process, runtime, state, start receipt, status, summary, snapshot receipt and log evidence.

Run BAT02 before recovery when the cause of a stop is not known. Upload only the generated `99_UPLOAD_PACKAGE.zip`. Do not delete locks or restart BAT03 before review.

### Post-restart health

`scripts/mochipoyo_alert_research/recovery/bat/06_audit_all_nine_restart_health.bat`

Run this only after the nine BAT03 windows have been restarted in order and each has completed at least one successful cycle.

The audit is read-only. It checks process count and runner identity, locks, frozen runtime SHA, immutable starts, loop status, successful and terminal cycle counts, latest output, private snapshot receipts and verified shared-journal relationships.

## Restart order

1. MT5 and CSV export
2. collector
3. M7C
4. M8C
5. M9V BAT03
6. M9Y BAT03
7. M10B BAT03
8. M10E BAT03
9. M10P BAT03
10. M10P2 BAT03
11. M10W19 BAT03
12. M10W26 BAT03
13. M10W34 BAT03
14. all-nine BAT06 health audit after one successful cycle per loop

## Immutable starts

- M9V: `2026.07.24 11:04:00`
- M9Y: `2026.07.24 12:45:00`
- M10B: `2026.07.24 20:54:00`
- M10E: `2026.07.24 22:06:00`
- M10P: `2026.07.24 23:56:00`
- M10P2: `2026.07.27 01:39:00`
- M10W19: `2026.07.28 02:31:00`
- M10W26: `2026.07.28 15:58:00`
- M10W34: `2026.07.28 18:19:00`

## Permanent prohibitions

- Never rerun an initialized BAT01 or initializer.
- Never rerun the historical one-time M10P incident recovery BAT02/BAT03.
- Never reset or edit a prospective start.
- Never recreate or manually edit runtime/state/start receipts.
- Never manually delete loop locks, bounded journals or private snapshots.
- Never use `taskkill` or force-close as recovery.
- Never backfill PC-off gaps from future data.
- Discord, MT5 orders, `live_ready`, `final_signal` and automatic promotion remain off.

## Verification

The implementation passed:

- Python syntax compilation for both new operators
- synthetic all-stopped recovery: all 11 protected lock files were archived first and only the active stale locks were removed
- synthetic running-process block: an active M10W34 process caused exit code 2 and preserved every active lock
- synthetic all-nine restart-health audit: 9 of 9 process/runtime/start/status/output/snapshot/journal checks passed and the upload package was produced

These tests used isolated temporary data and did not touch the user's real runtime or source CSVs.

## Status

Implementation is committed to the agent branch for review against `feature/mochipoyo-alert-research`. The operators have not been executed on the user's Windows machine and do not claim current local loop health.
