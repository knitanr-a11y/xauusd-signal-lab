# GOLD V3 Stage91 — Stage80 Ledger Sidecar Dry-Run Patch Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_91_STAGE80_LEDGER_SIDECAR_DRY_RUN_PATCH_AUDIT_ONLY`

Expected READY status after test run:

`GOLD_V3_80_IMMUTABLE_RUNTIME_MONITOR_READY_AUDIT_ONLY`

## 1. Purpose

Stage91 applies the Stage90 dry-run patch plan to Stage80 by adding optional ledger sidecar execution.

The default Stage80 behavior remains unchanged.

Default chain:

`Stage80 -> Stage76 -> Stage79`

Only when explicitly enabled:

`Stage80 -> Stage76 -> Stage79 -> Stage85 -> Stage86`

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

## 3. Patch target

Patched script:

`scripts/gold_v3_runtime/gold_v3_80_immutable_runtime_monitor_audit.py`

New optional args:

- `--enable-ledger-sidecar-dry-run`
- `--ledger-sidecar-nonblocking`

Default:

- sidecar disabled,
- no durable ledger append,
- no MT5,
- no Discord,
- no AI API,
- no final signal.

## 4. Sidecar behavior when enabled

When `--enable-ledger-sidecar-dry-run` is passed:

1. Stage80 runs Stage76.
2. Stage80 runs Stage79.
3. If Stage79 succeeds and paste path is available, Stage80 runs Stage85.
4. If Stage85 succeeds, Stage80 runs Stage86.
5. Stage80 records return codes, seconds, and paste paths for Stage85/86.
6. Stage80 writes these into state and summary.
7. Stage80 still does not append durable ledger.

If `--ledger-sidecar-nonblocking` is not passed, Stage85/86 failures block the Stage80 run.

If `--ledger-sidecar-nonblocking` is passed, Stage85/86 failures are recorded but do not block Stage80. This option is for troubleshooting only and should not be used as the normal safety mode.

## 5. Test BAT

Run:

`scripts/gold_v3_runtime/bat/run_gold_v3_91_stage80_ledger_sidecar_dry_run_patch_audit.bat`

This BAT runs Stage80 once with:

`--once --run-immediately --enable-ledger-sidecar-dry-run`

Paste:

`Files/FX_OUTPUTS/gold_v3/80_immutable_runtime_monitor_audit_only/gold_v3_80_PASTE_ME_IMMUTABLE_RUNTIME_MONITOR_SUMMARY.txt`

## 6. Expected summary additions

Stage80 summary should include:

- `ledger_sidecar_enabled`
- `ledger_sidecar_nonblocking`
- `last_stage85_returncode`
- `last_stage86_returncode`
- `last_stage85_seconds`
- `last_stage86_seconds`
- `last_stage85_paste_path`
- `last_stage86_paste_path`

## 7. Safety checks

Expected after normal default Stage80 run:

- `ledger_sidecar_enabled=false`

Expected after Stage91 BAT:

- `ledger_sidecar_enabled=true`
- `last_stage85_returncode=0`
- `last_stage86_returncode=0`
- `durable_ledger_append_enabled=false`
- `live_ready=false`
