# BTC AI V1 Day-Open Matched-Pair Shadow V1 Implementation

## Status

`IMPLEMENTED_READY_FOR_ONE_TIME_RUNTIME_INITIALIZATION`

The user authorized a fresh no-backfill matched-pair Shadow with Discord entry
notifications on 2026-08-05 JST. The implementation stays on the current research
branch. Isolation is enforced by frozen file paths and SHA256 verification rather
than by creating another branch.

## Frozen arms

1. `CONTROL_LOCK_0P25ATR`
2. `COOLDOWN_SKIP_NEXT_AFTER_INITIAL_STOP`

Both arms use the same broad H4 broker-day-open state, exact M1 entry, 4 ATR
initial stop, +2 ATR trigger, +0.25 ATR profit lock active from the next existing
M1, and state-flip exit. The cooldown arm skips exactly one new state episode
after an `INITIAL_SL` or `INITIAL_SL_GAP_OPEN` exit.

## Fresh activation

The repository does not contain the user's current MT5 CSV state or Discord
secret. Therefore the commit does not invent an activation cutoff. The one-time
`init` command must run on the machine where current CSV files exist. It records
the latest fully closed H4 as an immutable watermark; only later H4 decisions are
eligible.

## Discord

Each new state episode creates one idempotent audit notification containing the
exact M1 entry point and both arm statuses. If the cooldown arm skips, the same
notification explicitly records the skip. The webhook is supplied only through
`BTC_AI_V1_DAY_OPEN_SHADOW_DISCORD_WEBHOOK_URL`.

An entry is written to a durable outbox before network delivery. Delivery failure
does not erase the event; it remains retryable.

## Frozen/mutable boundary

Frozen:

- runtime implementation
- frozen contract and schemas
- activation authorization
- manifest hashes

Mutable by the runtime only:

- activation record
- current state
- event/action/trade/health ledgers
- Discord outbox and delivery ledger

Research may continue elsewhere on the same branch, but these frozen files must
not be edited. Any rule change requires V2 and a new no-backfill cutoff.

## Controls

- Stage55 unchanged
- MT5 orders OFF
- live trading OFF
- live-ready OFF
- final signal OFF
- Discord entry audit notifications ON after local initialization and secret setup
