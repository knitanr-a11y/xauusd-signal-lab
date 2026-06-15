# GOLD V3 118 DEMO ALERT-ONLY RESTART REVIEW AUDIT SPEC

Created JST: `2026-06-15`

## Status

```text
GOLD_V3_118_DEMO_ALERT_ONLY_RESTART_REVIEW_AUDIT_ONLY
```

## Scope

Stage118 is a restart review only. It does not start the demo loop, does not send Discord, does not change selected ledgers, and does not change source CSV contracts.

Allowed after this review, only with explicit user approval:

```text
demo Discord alert-only loop
scripts/gold_v3_runtime/bat/run_gold_v3_116_115_full_loop.bat
```

Still prohibited:

```text
MT5 execution
real account routing
live order path
final signal promotion
NO_SIGNAL Discord notification
F002 bypass
June 8 review-only restore auto adoption
overwrite of 109c / 107qc / 107r6c
```

## Required review points

1. The recommended BAT must remain demo alert-only.
2. Stage116 must use the exact selected 109c ledger only.
3. CSV latest row must remain treated as closed; open/as-of rows are not allowed.
4. If the latest closed candle is not present in the selected ledger, Stage116 must emit NO_SIGNAL.
5. Stage115A must not queue NO_SIGNAL.
6. Stage115B may send only queued demo alert-only notices.
7. Watchdog and BAT error branches may queue STOP_REVIEW notices only.
8. Stage118 itself must not start the loop.

## Expected decision values

PASS:

```text
DEMO_ALERT_ONLY_RESTART_REVIEW_PASS_USER_APPROVAL_REQUIRED
```

BLOCKED:

```text
DEMO_ALERT_ONLY_RESTART_REVIEW_BLOCKED
```
