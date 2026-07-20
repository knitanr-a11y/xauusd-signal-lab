# M7C M3 Foreign-Key Rebuild Incident — 2026-07-20

## Symptom

M7C prospective shadow loop detected new raw alerts and attempted the permitted M3/M4 derived refresh.

```text
[UPSTREAM_STALE] M3/M4 derived tables are stale relative to raw alerts
[ERROR] Episode build failed: FOREIGN KEY constraint failed
```

## Root cause

`rebuild_episodes()` deletes and recreates deterministic M3 episode rows inside one transaction.
Existing M5/M6-derived rows, including `feature_snapshots`, can retain foreign-key references to those deterministic episode IDs.
With immediate foreign-key checking, SQLite rejected the temporary in-transaction deletion before the same IDs were recreated.

This was an implementation defect in the automatic M7C stale-upstream refresh path. It was not a frozen-trigger failure and did not modify raw alerts, formulas, CSV inputs, Discord, MT5 orders, live-ready, or final-signal settings.

## Fix

Before the M3 transaction starts, the one-shot episode builder now enables:

```sql
PRAGMA defer_foreign_keys = ON;
```

Foreign-key enforcement remains enabled. Validation is delayed only until transaction commit.
The rebuild must recreate every referenced deterministic episode ID before commit; otherwise commit fails and the whole transaction rolls back.
No downstream M5/M6 rows are deleted.

## Regression coverage

Added:

```text
tests/mochipoyo_alert_research/test_episode_rebuild_foreign_keys.py
```

The test creates an episode, adds a downstream `feature_snapshots` reference, appends an EXIT alert, rebuilds M3 with deferred checking, and verifies:

- the episode closes correctly;
- the downstream snapshot remains;
- the episode ID remains unchanged;
- `PRAGMA foreign_key_check` is empty.

## User recovery

1. Stop only the M7C shadow loop.
2. Keep the Cloudflare collector running.
3. Pull `feature/mochipoyo-alert-research`.
4. Restart `run_m7c_prospective_shadow_forever.bat`.

The loop will detect the same stale M3/M4 state, perform the corrected derived refresh, and rerun the unchanged M7C manifest.
