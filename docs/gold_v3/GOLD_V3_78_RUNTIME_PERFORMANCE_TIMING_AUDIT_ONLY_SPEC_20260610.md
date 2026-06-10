# GOLD V3 Stage78 — Runtime Performance Timing Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_78_RUNTIME_PERFORMANCE_TIMING_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_78_RUNTIME_PERFORMANCE_TIMING_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_78_RUNTIME_PERFORMANCE_TIMING_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage78 measures the real runtime cost of the current audit-only detection loop.

It answers:

- How long does the idle latest-row CSV check take?
- How long does Stage74 one-shot take?
- How long does Stage75 payload preview take?
- How long does the full new-candle audit run take?

Stage78 does not optimize by approximation and does not enable any external side-effect.

## 2. Non-negotiable constraints

- GOLD V3 only.
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

The human clarified:

`open中の足はCSVには入りません`

Stage78 must preserve:

- `csv_contract: open/in-progress candles are not written to CSV`
- `csv_open_bar_exclusion_required: false`

The latest row in `goldsharp_m15.csv` is the latest closed M15 row.

## 4. Required inputs

Default Files directory:

`Files`

Required CSV:

- `goldsharp_m15.csv`

Required scripts:

- `scripts/gold_v3_runtime/gold_v3_74_guarded_live_csv_monitor_audit.py`
- `scripts/gold_v3_runtime/gold_v3_75_external_action_payload_preview_audit.py`

## 5. What Stage78 measures

Stage78 runs:

1. latest-row-only CSV time check,
2. Stage74 one-shot,
3. Stage75 payload preview.

It writes a timing row for each segment and a total.

## 6. Timing thresholds

Advisory thresholds:

- `latest_row_check_seconds <= 0.25`
- `stage74_seconds <= 10.0`
- `stage75_seconds <= 2.0`
- `total_full_audit_seconds <= 12.0`

Hard blocker threshold:

- `total_full_audit_seconds <= 60.0`

Exceeding an advisory threshold produces WARN but does not necessarily block. Exceeding the hard blocker threshold blocks.

## 7. READY conditions

Stage78 is READY if:

- required CSV exists,
- required scripts exist,
- latest-row-only time check succeeds,
- Stage74 returns zero,
- Stage75 returns zero,
- Stage75 summary is READY,
- Stage75 latest closed M15 time matches the current CSV latest M15 time,
- all external side-effect flags remain false,
- total full audit runtime is under the hard blocker threshold,
- `csv_open_bar_exclusion_required=false` is preserved.

READY only means timing data was captured safely. It does not mean live release is approved.

## 8. Outputs

Output folder:

`Files/FX_OUTPUTS/gold_v3/78_runtime_performance_timing_audit_only`

Required outputs:

- `gold_v3_78_runtime_timing.csv`
- `gold_v3_78_performance_assessment.csv`
- `gold_v3_78_blocker_matrix.csv`
- `gold_v3_78_validation_matrix.csv`
- `gold_v3_78_runtime_performance_timing_summary.json`
- `gold_v3_78_PASTE_ME_RUNTIME_PERFORMANCE_TIMING_SUMMARY.txt`
- `GOLD_V3_78_REPORT.md`

## 9. Runner and BAT

Script:

`scripts/gold_v3_runtime/gold_v3_78_runtime_performance_timing_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_78_runtime_performance_timing_audit.bat`

The BAT is a one-shot timing audit. It does not send notifications or place trades.
