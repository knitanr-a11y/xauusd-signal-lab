# GOLD V3 Stage92 — Stage80 Default No-Sidecar Regression Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_92_STAGE80_DEFAULT_NO_SIDECAR_REGRESSION_AUDIT_ONLY`

READY status:

`GOLD_V3_92_STAGE80_DEFAULT_NO_SIDECAR_REGRESSION_READY_AUDIT_ONLY`

BLOCKED status:

`GOLD_V3_92_STAGE80_DEFAULT_NO_SIDECAR_REGRESSION_BLOCKED_AUDIT_ONLY`

## Purpose

Stage92 verifies that the Stage91 optional ledger sidecar patch did not change normal Stage80 behavior.

Stage80 must keep ledger sidecar OFF unless explicitly enabled.

## Required constraints

- GOLD V3 only.
- Audit-only.
- No external action.
- No live release.
- Do not mutate candidate pool.
- Keep: `poolから外さない。rolling health gateに判断させる。`
- Keep CSV contract: `open/in-progress candles are not written to CSV`.
- Keep `csv_open_bar_exclusion_required=false`.

## Test invocation

Stage92 runs Stage80 once with:

```bat
--once --run-immediately --no-startup-run
```

Stage92 must not pass:

```bat
--enable-ledger-sidecar-dry-run
```

## Outputs

Short output folder:

`Files/FX_OUTPUTS/gold_v3/92c/`

Outputs:

- `paste_me.txt`
- `summary.json`
- `validation.csv`
- `blockers.csv`
- `report.md`

## READY conditions

- Stage80 script exists.
- Stage80 default invocation returns 0.
- Stage80 summary exists.
- Stage80 status is READY.
- `ledger_sidecar_enabled=false`.
- `durable_ledger_append_enabled=false`.
- `live_ready=false`.
- blocker_count is zero.

## Next if READY

Use the regular Stage80 BAT for normal monitoring.

Use Stage91 BAT only when explicitly testing sidecar dry-run.
