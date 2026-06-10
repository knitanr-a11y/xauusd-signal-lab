# GOLD V3 Stage80 — Immutable Runtime Monitor Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_80_IMMUTABLE_RUNTIME_MONITOR_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_80_IMMUTABLE_RUNTIME_MONITOR_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_80_IMMUTABLE_RUNTIME_MONITOR_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage80 is the operational audit-only monitor wrapper.

It watches `goldsharp_m15.csv` at every minute + 5 seconds. When a new closed M15 row is detected, it runs:

1. Stage76 one-shot full audit monitor with payload preview,
2. Stage79 immutable runtime output snapshot.

This avoids relying only on overwritten latest files during future operation. Stage76 latest files may still exist as scratch/current-state files, but Stage79 creates the immutable evidence snapshot for each detected M15 run.

## 2. Non-negotiable constraints

- GOLD V3 only.
- GOLD V2, old GOLD, and DISC8 remain quarantined.
- Do not read, use, reference, compare against, or fallback to GOLD V2, old GOLD, or DISC8.
- Do not use Stage41 feature-only snapshot as a trading source.
- Do not create MT5 order BATs.
- Do not send Discord notifications.
- Do not call AI APIs.
- Do not enable live hook, live evaluator, or final signal.
- Do not manually remove or demote candidates/profiles.
- Keep every observed candidate in the pool.
- Required pool policy:

`poolから外さない。rolling health gateに判断させる。`

## 3. CSV closed-row contract

Preserve:

- `csv_contract: open/in-progress candles are not written to CSV`
- `csv_open_bar_exclusion_required: false`

The latest row in `goldsharp_m15.csv` is the latest closed M15 row.

## 4. Runtime model

- Idle heartbeat: read only the latest CSV row timestamp.
- New closed M15 timestamp: run Stage76 `--once`, then Stage79.
- Evidence: Stage79 run_id directory under short root `FX_OUTPUTS/gold_v3/79i/YYYYMMDD/RUN_ID/`.
- Stage80 state/log files are minimal monitor bookkeeping, not the source evidence.

## 5. READY conditions

Stage80 one-shot smoke mode is READY if:

- required CSV exists,
- Stage76 runner exists,
- Stage79 runner exists,
- latest closed M15 timestamp is readable from the latest CSV row,
- Stage76 one-shot returns 0,
- Stage79 returns 0,
- Stage79 paste path is detected,
- all live/external side-effect flags remain false,
- blocker_count is zero.

For continuous monitor mode, READY is maintained in `gold_v3_80_state.json` and appended to `gold_v3_80_event_log.csv`.

## 6. Outputs

Output folder:

`Files/FX_OUTPUTS/gold_v3/80_immutable_runtime_monitor_audit_only/`

Fixed monitor bookkeeping outputs:

- `gold_v3_80_state.json`
- `gold_v3_80_event_log.csv`
- `gold_v3_80_timing_log.csv`
- `gold_v3_80_blocker_matrix.csv`
- `gold_v3_80_validation_matrix.csv`
- `gold_v3_80_immutable_runtime_monitor_summary.json`
- `gold_v3_80_PASTE_ME_IMMUTABLE_RUNTIME_MONITOR_SUMMARY.txt`
- `GOLD_V3_80_REPORT.md`

Immutable evidence outputs are created by Stage79 under:

`Files/FX_OUTPUTS/gold_v3/79i/YYYYMMDD/RUN_ID/`

## 7. Runner and BAT

Script:

`scripts/gold_v3_runtime/gold_v3_80_immutable_runtime_monitor_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_80_immutable_runtime_monitor_audit.bat`

The BAT opens a continuous audit-only monitor. Use `Ctrl+C` or close the window to stop.
