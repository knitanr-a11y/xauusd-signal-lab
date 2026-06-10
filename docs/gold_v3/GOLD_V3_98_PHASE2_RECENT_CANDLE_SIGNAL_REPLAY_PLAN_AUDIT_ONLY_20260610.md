# GOLD V3 Stage98 — Phase2 Recent Candle Signal Replay Plan Audit-Only

Created JST: `2026-06-10`

Status target:

`GOLD_V3_98_PHASE2_RECENT_CANDLE_SIGNAL_REPLAY_PLAN_READY_AUDIT_ONLY`

## Human decision

The human wants to skip old Phase1 and Phase3.

Adopted flow:

```text
Phase2: recent closed-candle signal replay / signal-only dry run
Phase4: micro-lot guarded live, only after separate approval
```

Do not do:

```text
Phase1: monitor-only shadow phase
Phase3: manual approval phase
```

## Why Phase2 is required

Before any MT5 order path is enabled, the current live-style signal detection path must be tested against recent closed candles.

Goal:

```text
recent closed M15 candles -> replay each as latest closed row -> Stage80/76 signal path -> record decision
```

This confirms signal detection behavior without live order execution.

## Replay principle

Do not approximate or reimplement trading rules.

Use the existing live-style entry path.

Preferred replay method:

1. Create a temporary replay candle directory for each target M15 timestamp.
2. Truncate candle CSVs so that the selected timestamp is the latest row.
3. Run Stage80 once with signal-gated sidecar enabled.
4. Record whether decision is NO_SIGNAL, SIGNAL, or UNKNOWN.
5. Never write orders, notifications, AI calls, or durable trade ledger appends.

## Required safety constraints

- GOLD V3 only.
- Audit-only.
- No MT5 order execution.
- No Discord live notification.
- No AI API call.
- No final signal release.
- No durable ledger append.
- No candidate pool mutation.
- CSV contract remains closed-row only.

## Suggested replay size

Default:

```text
recent_m15_bars: 64
```

Optional:

```text
recent_m15_bars: 32 / 96 / 128
```

## Success criteria

Stage99 implementation should pass if:

- replay input folders are generated safely,
- no source candle CSV is modified,
- Stage80 can run per replay point,
- decisions are recorded for all replay points or explicit blockers are emitted,
- SIGNAL rows, if any, produce Stage85/86 preview/guard outputs,
- NO_SIGNAL rows skip Stage85/86 in signal-gated mode,
- all live/external flags remain false.

## Next stage

Implement replay harness:

`GOLD_V3_99_RECENT_CLOSED_CANDLE_SIGNAL_REPLAY_AUDIT_ONLY`
