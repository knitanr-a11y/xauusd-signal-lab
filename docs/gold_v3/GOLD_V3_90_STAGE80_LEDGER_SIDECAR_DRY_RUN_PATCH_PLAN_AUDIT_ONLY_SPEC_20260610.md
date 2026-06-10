# GOLD V3 Stage90 — Stage80 Ledger Sidecar Dry-Run Patch Plan Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_90_STAGE80_LEDGER_SIDECAR_DRY_RUN_PATCH_PLAN_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_90_STAGE80_LEDGER_SIDECAR_DRY_RUN_PATCH_PLAN_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_90_STAGE80_LEDGER_SIDECAR_DRY_RUN_PATCH_PLAN_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage90 creates a dry-run patch plan for connecting ledger sidecar checks to the Stage80 runtime monitor.

It does not modify Stage80.

The intended future chain is:

`Stage80 -> Stage76 -> Stage79 -> Stage85 -> Stage86`

This stage identifies the safest insertion point and writes a human-readable patch plan.

## 2. Non-negotiable constraints

- GOLD V3 only.
- GOLD V2, old GOLD, and DISC8 remain quarantined.
- Do not read, use, reference, compare against, or fallback to GOLD V2, old GOLD, or DISC8.
- Do not use Stage41 feature-only snapshot as a trading source.
- GOLD V3 remains audit-only.
- Do not send Discord notifications.
- Do not place MT5 orders.
- Do not call AI APIs.
- Do not enable live hook, live evaluator, or final signal.
- Do not manually remove or demote candidates/profiles.
- Required pool policy:

`poolから外さない。rolling health gateに判断させる。`

## 3. CSV closed-row contract

Preserve:

- `csv_contract: open/in-progress candles are not written to CSV`
- `csv_open_bar_exclusion_required: false`

## 4. Dry-run patch target

Target script:

`scripts/gold_v3_runtime/gold_v3_80_immutable_runtime_monitor_audit.py`

The safe insertion point is after Stage79 succeeds and after `last_stage79_paste_path` is extracted, but before `last_seen = latest` is committed.

Reason:

- Stage85 needs Stage76 summary and Stage79 evidence path context.
- Stage86 needs Stage85 output.
- If Stage85/86 fails, Stage80 should not mark the M15 run as fully processed unless the future patch explicitly defines a non-blocking mode.

## 5. Proposed future behavior

A future patch may add optional args:

- `--enable-ledger-sidecar-dry-run`
- `--ledger-sidecar-nonblocking`

Default must remain disabled.

Default Stage80 behavior must remain unchanged unless the option is explicitly passed.

When enabled in a future dry-run patch:

1. Run Stage76.
2. Run Stage79.
3. If Stage79 is OK and paste path exists, run Stage85.
4. If Stage85 is OK, run Stage86.
5. Record sidecar timings and return codes in Stage80 timing log.
6. Add fields to Stage80 state/summary:
   - `ledger_sidecar_enabled`
   - `last_stage85_returncode`
   - `last_stage86_returncode`
   - `last_stage85_seconds`
   - `last_stage86_seconds`
   - `last_stage85_paste_path`
   - `last_stage86_paste_path`
7. Do not append durable trade ledger.
8. Do not send Discord, MT5, AI API, or final signal.

## 6. Outputs

Short output folder:

`Files/FX_OUTPUTS/gold_v3/90c/`

Outputs:

- `paste_me.txt`
- `summary.json`
- `patch_plan.md`
- `patch_plan.csv`
- `insertion_point_matrix.csv`
- `blockers.csv`
- `validation.csv`
- `report.md`

## 7. READY conditions

Stage90 is READY if:

- Stage80 script exists,
- Stage85/86 scripts exist,
- Stage89 summary is READY,
- Stage80 has recognizable Stage76 and Stage79 execution points,
- Stage80 has a recognizable `last_seen = latest` commit point,
- patch plan is written,
- Stage80 is not modified by Stage90,
- sidecar autorun remains disabled,
- no durable ledger append is enabled,
- no live/external flags are enabled,
- blocker_count is zero.

## 8. Next stage if READY

If READY, the next stage may be:

`GOLD_V3_91_STAGE80_LEDGER_SIDECAR_DRY_RUN_PATCH_AUDIT_ONLY`

Stage91 should still keep sidecar disabled by default and must remain audit-only.
