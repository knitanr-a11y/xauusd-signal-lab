# Stage M6C Exit-Reference Boundary Correction

Status: audit-only correction  
Boundary contract: `MOCHIPOYO_M6C_EXIT_REFERENCE_BOUNDARY_V2`

## Incident

The first real-data M6C run stopped with:

```text
candidate M5_SECOND_BOTTOM_TOP_BREAK_CLOSE occurs at/after exit reference
```

The source EXIT timestamp can contain seconds. For example, an EXIT at
`11:00:02` is later than an M5 close at `11:00:00`, so the original M5 search
window admitted that trigger.

The MT5-only paired comparison uses the final fully closed M1 close before the
source EXIT minute. In this example that exit reference is also `11:00:00`.
Therefore the candidate and comparison exit have no positive holding interval.

This is not future leakage and does not invalidate the other entries. The
candidate is simply too late for the defined paired outcome measurement.

## Correction

For every closed source entry:

1. compute the exact MT5 exit-reference timestamp first;
2. search M5 candidates only when the trigger close is strictly earlier than
   that timestamp;
3. treat candidates at or after the exit reference as missed;
4. do not abort the complete M6C audit because of one late candidate.

Open source episodes keep their latest-closed-M5 analysis boundary and are not
changed by this correction.

## Safety

The correction does not modify:

- raw alerts;
- episode assignments;
- MT5 alignment;
- M5 feature snapshots;
- M6A virtual entries or outcomes;
- M6B context rows.

Entry gates, rule approval, Discord sending, MT5 orders, live-ready state, and
final signals remain disabled.
