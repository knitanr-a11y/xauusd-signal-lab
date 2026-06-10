# GOLD V3 Stage96 — Stage80 Default No Signal-Gated Regression Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_96_STAGE80_DEFAULT_NO_SIGNAL_GATED_REGRESSION_AUDIT_ONLY`

READY status:

`GOLD_V3_96_STAGE80_DEFAULT_NO_SIGNAL_GATED_REGRESSION_READY_AUDIT_ONLY`

BLOCKED status:

`GOLD_V3_96_STAGE80_DEFAULT_NO_SIGNAL_GATED_REGRESSION_BLOCKED_AUDIT_ONLY`

## Purpose

Verify that the Stage95 option remains OFF in normal Stage80 mode.

Stage96 runs Stage80 once with default options and checks:

```text
ledger_sidecar_enabled=false
signal_gated_sidecar_enabled=false
durable_ledger_append_enabled=false
```

## Input

Stage80 summary:

```text
Files/FX_OUTPUTS/gold_v3/80_immutable_runtime_monitor_audit_only/gold_v3_80_immutable_runtime_monitor_summary.json
```

## Output

Short folder:

```text
Files/FX_OUTPUTS/gold_v3/96c/
```

Main paste:

```text
paste_me.txt
```

## Next if READY

Update the runtime manual with Stage95 and Stage96 results.
