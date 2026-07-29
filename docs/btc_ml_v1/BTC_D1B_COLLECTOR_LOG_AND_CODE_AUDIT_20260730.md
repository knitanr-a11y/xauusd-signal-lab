# BTC D1B — Collectorログ・実装・DB契約監査

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T07:01:00+09:00`
- result: `D1B_COLLECTOR_PROVENANCE_CONTRACT_AUDITED_BCR01_SNAPSHOT_NEXT`
- performance interpretation: not performed

## 1. User package

Upload: `新しい圧縮された (ZIP) フォルダー(1).zip`

ZIP SHA256:

`b65ddd0b7c240d5acd26c271b228142929574d82ad5e96eadec1e1f37d62b3fe`

Files:

| file | bytes | SHA256 |
|---|---:|---|
| `collector_forever.log` | 8,315,891 | `77b8aa35492fcf88c5687e3a9569987546295ef280057d99b0235289ac5dcc05` |
| `latest_collection_error.json` | 1,397 | `ac897147c805a3fff261bb5c0d0b98c9772978a4d4dc9faca4e6a1297595ca41` |
| `latest_collection_result.json` | 591 | `09340d3a95d2b48959032b39ffc1c98a0a591a9faa780e6f9f8076cdd21918a3` |
| `latest_loop_status.json` | 905 | `da65cf404422e2ea94171f00f7b24d4e4b61706bc925b9efea6ba56516e5c228` |

## 2. Collector runtime continuity

The complete log contains two loop runs:

1. `2026-07-20T14:51:00Z` through `2026-07-22T18:59:04Z`, cycles `1–3111`.
2. `2026-07-23T06:32:27Z` through `2026-07-29T22:01:00Z`, cycles `1–9501`.

Combined cycle headers: `12,612`.

- successful cycles: `12,606`
- failed cycles: `6`
- PASS: `118`
- PASS_EMPTY: `12,488`
- Cloudflare response rows: `127`
- inserted rows: `127`
- duplicate rows: `0`

The second run started from preserved cursor `94` and immediately recovered IDs `95–103` in one page. This is consistent with the frozen forced-reboot recovery contract: loop counters may restart, while the SQLite cursor and prospective start remain preserved.

## 3. Six failed cycles

All six failures were Cloudflare HTTP 500 / Error 1101 `worker_threw_exception`:

- current-run cycle 133 at cursor 104
- cycle 207 at cursor 105
- cycle 878 at cursor 109
- cycle 1400 at cursor 114
- cycle 5454 at cursor 140
- cycle 8088 at cursor 169

For every failure:

- the cursor did not advance;
- the next cycle retried from the same cursor;
- one new event was recovered successfully;
- no duplicate was inserted.

This matches the implementation contract: failure records `cursor_preserved_at`, and `last_successful_id` is only updated inside the successful SQLite transaction.

## 4. Cursor and page invariants

Across all successful cycles:

- `response_count = inserted_count + duplicate_count`
- `cursor_after >= after_id_before`
- `cursor_after - after_id_before = response_count`
- PASS_EMPTY always had zero response rows
- PASS always had one or more response rows
- no cursor regression was observed

The latest result advanced cursor `188 -> 189`. The earlier M7C evidence package ended at raw alert ID `188`, because its report was built before ID 189 arrived. This is not a mismatch.

## 5. Misleading stale error artifact

`latest_collection_error.json` describes the older cycle-8088 failure at cursor 169, while the current loop status is RUNNING and the latest success cursor is 189.

Cause:

- the one-shot collector deletes the legacy error file after success;
- the organized wrapper moves diagnostics into the Collector folder;
- when no new source error exists, it does not delete the old target error file.

Therefore `latest_collection_error.json` is not authoritative by itself. Current state must be determined from `latest_loop_status.json`, the latest successful result, and log chronology. This is recorded as a diagnostic freshness defect, not a Collector data-loss event. No Collector code is modified during D1.

## 6. Exact Collector contract

The exact read-only implementation files inspected were:

- `scripts/mochipoyo_alert_research/run_collect_events_cloudflare_forever.bat`
- `scripts/mochipoyo_alert_research/run_collect_events_forever.py`
- `scripts/mochipoyo_alert_research/collect_events_once_organized.py`
- `scripts/mochipoyo_alert_research/collect_events_once.py`
- `scripts/mochipoyo_alert_research/db.py`
- `scripts/mochipoyo_alert_research/schema.sql`

The collector requests:

`/events?after_id=<last_successful_id>&limit=500`

The Worker row contract requires:

- `id`
- `received_at_utc`
- `source=tradingview`
- `strategy=mochipoyo`
- event in LONG / SHORT / LONG_EXIT / SHORT_EXIT
- ticker in BTCUSD / XAUUSD
- `bar_time_utc`
- `fired_at_utc`

The Collector additionally stores:

- `downloaded_at_utc`: local Collector fetch/store time
- `worker_raw_json`
- exact `collector_source_row_json`
- SHA256 of canonical source row
- event key and its origin
- OHLC/message fields when present

## 7. Immutable collision behavior

Each page must have:

- ascending IDs;
- no duplicate IDs;
- every ID greater than requested `after_id`;
- no duplicate event keys.

An existing ID/event key is accepted only when both identity and payload SHA256 are exactly identical. Any changed payload for an existing identity raises `ImmutableCollisionError` and rolls back the page. Cursor advancement and inserts occur in one `BEGIN IMMEDIATE` transaction.

## 8. Why the full SQLite DB must not be uploaded

The schema contains both source/provenance tables and later research tables.

Outcome-blind allowlist:

- `collector_state`
- `raw_alerts`
- `raw_alert_annotations`
- `collection_runs`

Forbidden for the next snapshot:

- `episodes`
- `episode_events`
- `episode_build_anomalies`
- `episode_build_runs`
- `mt5_alignment`
- `feature_snapshots`
- `virtual_entries`
- `outcomes`

The raw SQLite DB must not be copied or uploaded because it may contain result-bearing rows in `outcomes` and related tables. The next stage creates a logical read-only export of only the four allowlisted source tables.

## 9. D1B conclusion

Accepted:

- Collector loop status and cursor behavior
- failure recovery behavior
- exact source-row storage contract
- three distinct timestamps: `bar_time_utc`, `fired_at_utc`, `received_at_utc`
- Collector fetch timestamp: `downloaded_at_utc`
- immutable raw payload and hash contract
- no duplicate insertion in the inspected period

Still requiring logical source snapshot:

- actual values and distributions of all four timestamps
- exchange/timeframe/source price identifiers
- raw payload key inventory
- connection-test annotations
- raw event rows for exact BTC event ledger construction

## 10. Next stage

`BCR01_OUTCOME_BLIND_SOURCE_SNAPSHOT`

A BTC-side script opens the active SQLite database in read-only/query-only mode, starts one consistent read transaction, and exports only the four allowlisted source tables. Collector/M7C remain running and unchanged. Outcome-bearing tables are not queried or exported.
