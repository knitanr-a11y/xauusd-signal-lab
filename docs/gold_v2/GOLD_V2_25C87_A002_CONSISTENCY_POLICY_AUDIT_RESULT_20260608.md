# GOLD V2 25C87 A002 consistency policy audit result

Created UTC: 2026-06-08

Status: `A002_CONSISTENCY_POLICY_POSSIBLE_NOT_ORIGINAL_SOT`

## Purpose

Answer whether A002 can be made internally consistent from the currently available evidence, even though the original top-ledger cluster representative profit logic is not recovered.

This is audit-only. It does not approve source recovery, live evaluator, final signal, Discord, MT5, or AI.

## Answer

Yes, A002 can be made internally consistent **if** it is clearly separated from original SOT recovery.

The correct wording is:

```text
A002 membership is source-proven and OHLC-reproducible.
A002 representative profit is not original-source-proven.
Therefore an A002 event-level evaluation may be defined as a transparent consistency policy, not as recovered original SOT.
```

## Evidence already established

| item | status |
| --- | --- |
| A002 772 event membership | PROVEN_EXACT |
| raw RR125 row universe | PROVEN_EXACT |
| raw outcome replay | NEAR_EXACT |
| original cluster representative profit logic | NOT_FOUND |
| A002 original WR/PF | BLOCKED |
| A002 consistency-policy WR/PF | POSSIBLE_IF_LABELED_NEW_POLICY |

13C5 explicitly found zero true original clustering candidate files, so original representative profit recovery is not supported by that artifact.

## Available raw rows under A002

A002 events: 772

Raw rows joined by `dataset + entry_time + policy`: 2828

Only 56 / 772 events have a unique `profit_r + exit_time` assignment. Therefore using the original representative profit remains blocked.

## Tested transparent event-level policies

These policies do not claim to be original SOT. They are deterministic ways to summarize multiple raw rows per A002 event.

| policy | count | wins | losses | breakeven | win_rate | pf | total_r | comment |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| RAW_ROWS_ALL_2828_NOT_EVENT | 2828 | 1444 | 1381 | 3 | 51.0608% | 1.230584 | 288.051467 | raw-row level, not event-level |
| STRICT_UNIQUE_ONLY_56_EVENTS | 56 | 16 | 39 | 1 | 28.5714% | 0.427521 | -22.326667 | only unambiguous subset |
| EVENT_WORST_RAW_MIN | 772 | 246 | 525 | 1 | 31.8653% | 0.501893 | -247.154000 | conservative lower-bound |
| EVENT_BEST_RAW_MAX | 772 | 531 | 240 | 1 | 68.7824% | 2.941156 | 394.320000 | optimistic upper-bound |
| EVENT_MEAN_OF_RAW_ROWS | 772 | 433 | 338 | 1 | 56.0881% | 1.311195 | 76.533363 | event-level mean of candidates |
| EVENT_MEDIAN_OF_RAW_ROWS | 772 | 442 | 329 | 1 | 57.2539% | 1.311323 | 90.871400 | event-level median of candidates |
| EVENT_EARLIEST_EXIT_THEN_RAW_ORDER | 772 | 328 | 443 | 1 | 42.4870% | 0.888081 | -47.993333 | deterministic earliest exit |
| EVENT_LATEST_EXIT_THEN_RAW_ORDER | 772 | 449 | 322 | 1 | 58.1606% | 1.717114 | 194.021200 | deterministic latest exit |
| EVENT_FIRST_RAW_ORDER | 772 | 353 | 418 | 1 | 45.7254% | 0.975625 | -9.652133 | deterministic file order first |
| EVENT_LAST_RAW_ORDER | 772 | 430 | 341 | 1 | 55.6995% | 1.574114 | 171.756400 | deterministic file order last |

## Recommended consistency convention

If a single A002 event-level evaluation is required without original representative logic, use:

```text
primary: EVENT_WORST_RAW_MIN
secondary sensitivity: EVENT_MEAN_OF_RAW_ROWS and EVENT_BEST_RAW_MAX
```

Reason:

- `EVENT_WORST_RAW_MIN` cannot overstate performance.
- It is deterministic.
- It is fully explainable.
- It does not invent original source logic.
- It gives a conservative lower-bound for A002 event quality.

However, it should be labeled as:

```text
A002_CONSERVATIVE_CONSISTENCY_POLICY
```

not:

```text
A002_ORIGINAL_SOT_RESULT
```

## What is acceptable to say

Allowed:

```text
A002 membership is exact and reproducible.
Under a conservative event-level consistency policy, A002 has WR 31.8653%, PF 0.501893.
Under event mean/median candidate summaries, A002 is positive, with PF around 1.31.
Under optimistic upper-bound, PF is 2.94.
```

Not allowed:

```text
The original A002 strategy win-rate is X.
The original A002 PF is X.
A002 representative profit has been recovered.
```

## Decision

A002 can be made internally consistent as an event-set plus transparent evaluation policy. This is useful for research and for deciding whether A002 has enough signal density to continue investigating.

But it cannot be promoted to recovered original SOT without the missing representative profit logic or membership ledger.

## Next suggested step

`25C88_A002_CONSISTENCY_POLICY_FREEZE_AUDIT_ONLY`

Freeze a clearly-labeled conservative A002 consistency policy:

```text
A002 event membership: exact reproduced set of 772
representative result: worst raw profit per event
reporting: include mean/median/best sensitivity, but primary uses worst-case
live/final: still off
```
