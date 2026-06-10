# GOLD V3 Stage99 — Recent Closed Candle Signal Replay Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_99_RECENT_CLOSED_CANDLE_SIGNAL_REPLAY_AUDIT_ONLY`

READY status:

`GOLD_V3_99_RECENT_CLOSED_CANDLE_SIGNAL_REPLAY_READY_AUDIT_ONLY`

## Purpose

Replay recent closed M15 candles through the live-style Stage80 path.

This replaces the skipped Phase1/Phase3 with a stronger Phase2 check:

```text
recent closed M15 candles -> temporary truncated CSV folder -> Stage80 signal-gated run -> decision log
```

## Rules

- Do not modify source CSV files.
- Do not reimplement signal rules.
- Use Stage80 / Stage76 path.
- Use `--enable-signal-gated-ledger-sidecar`.
- No live execution.
- No notification.
- No AI call.
- No durable append.

## Default run size

```text
--bars 32
```

Can be changed to:

```text
--bars 64
```

## Outputs

Folder:

`Files/FX_OUTPUTS/gold_v3/99c/`

Files:

- `paste_me.txt`
- `summary.json`
- `replay_results.csv`
- `signal_rows.csv`
- `validation.csv`
- `blockers.csv`
- `report.md`

## Success criteria

- Source CSVs are unchanged.
- Replay input folders are created under Stage99 output only.
- Stage80 returns zero for each replay point.
- Each replay point has a decision: `NO_SIGNAL` or `SIGNAL`.
- NO_SIGNAL rows skip Stage85/86.
- SIGNAL rows run Stage85/86.
- Live/external flags remain false.
