# GOLD V3 Stage94 — Signal-Gated Stage80 Sidecar Patch Plan Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_94_SIGNAL_GATED_STAGE80_SIDECAR_PATCH_PLAN_AUDIT_ONLY`

READY status:

`GOLD_V3_94_SIGNAL_GATED_STAGE80_SIDECAR_PATCH_PLAN_READY_AUDIT_ONLY`

BLOCKED status:

`GOLD_V3_94_SIGNAL_GATED_STAGE80_SIDECAR_PATCH_PLAN_BLOCKED_AUDIT_ONLY`

## Purpose

Stage94 plans a future Stage80 patch that runs ledger sidecar only when the current closed M15 produces a real SIGNAL.

It does not patch Stage80.

## Current proven state

- Stage91 proved explicit sidecar dry-run works.
- Stage92 proved normal Stage80 keeps sidecar OFF by default.
- Stage93 proved current NO_SIGNAL is suppressed and not appended.

## Future target chain

Normal default remains:

```text
Stage80 -> Stage76 -> Stage79
```

Future optional signal-gated mode:

```text
Stage80 -> Stage76 -> Stage79 -> if SIGNAL then Stage85 -> Stage86
```

If NO_SIGNAL:

```text
Stage80 -> Stage76 -> Stage79 -> skip Stage85/86
```

## Required constraints

- GOLD V3 only.
- Audit-only.
- No live release.
- No external action.
- No durable ledger append.
- Do not mutate candidate pool.
- Keep CSV contract: `open/in-progress candles are not written to CSV`.
- Keep `csv_open_bar_exclusion_required=false`.
- Keep pool policy: `poolから外さない。rolling health gateに判断させる。`

## Planned future patch

Add optional arg:

```text
--enable-signal-gated-ledger-sidecar
```

Default must be OFF.

Add decision extraction after Stage79 paste path is known.

Decision source priority:

1. Stage76/Stage79 structured summary if available.
2. Stage79 immutable run folder name if it contains `NO_SIGNAL` or signal marker.
3. Block as `DECISION_NOT_DETECTABLE`.

Patch behavior:

- If decision is NO_SIGNAL: skip Stage85/86 and record skip reason.
- If decision is SIGNAL: run Stage85 then Stage86.
- If decision is UNKNOWN: block in strict mode.

## Outputs

Short output folder:

`Files/FX_OUTPUTS/gold_v3/94c/`

Outputs:

- `paste_me.txt`
- `summary.json`
- `patch_plan.csv`
- `decision_gate_design.csv`
- `validation.csv`
- `blockers.csv`
- `report.md`

## Next if READY

If READY, next stage may implement the optional signal-gated Stage80 patch:

`GOLD_V3_95_SIGNAL_GATED_STAGE80_SIDECAR_PATCH_AUDIT_ONLY`
