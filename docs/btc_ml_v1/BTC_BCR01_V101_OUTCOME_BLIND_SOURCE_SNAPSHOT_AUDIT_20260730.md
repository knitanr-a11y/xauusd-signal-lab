# BTC BCR01 v1.0.1 — outcome-blind source snapshot audit

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30`
- input package: `99_UPLOAD_PACKAGE(102).zip`
- package SHA256: `bc562948ee8baefba32d0e291a54341243da4684bdbf43d652676d5fcdab5611`
- result: `ACCEPTED_READY_OUTCOME_BLIND_SOURCE_SNAPSHOT`
- performance interpretation: not performed

## 1. Package acceptance

The package contains the exact ten required members:

1. `00_READ_ME_FIRST.txt`
2. `01_snapshot_summary.json`
3. `02_source_schema_manifest.json`
4. `03_collector_state.csv`
5. `04_raw_alerts_manifest.csv`
6. `05_raw_alerts_payloads.jsonl`
7. `06_raw_alert_annotations.csv`
8. `07_collection_runs.csv`
9. `08_integrity_checks.json`
10. `09_runtime_file_observation.json`

Snapshot ID: `BCR01_20260730T030649Z_RAWMAX194`

BCR01 version: `1.0.1`

## 2. Source integrity

Accepted values:

- raw alert rows: `194`
- raw alert ID range: `1–194`
- IDs contiguous: independently verified
- last successful Collector cursor: `194`
- cursor equals maximum raw ID: true
- duplicate raw IDs: `0`
- duplicate event keys: `0`
- payload SHA256 mismatches: `0`
- source JSON parse errors: `0`
- source identity mismatches: `0`
- annotation orphans: `0`
- collection run duplicate IDs: `0`
- invalid collection statuses: `0`
- Cloudflare cursor regressions: `0`

All 194 source rows use one exact key contract and are `source=tradingview`, `strategy=mochipoyo`, `exchange_name=VANTAGE`, `timeframe=15`. All event keys are derived from Cloudflare IDs because the Worker rows did not contain an event key. `worker_raw_json` and `collector_source_row_json` are identical for all 194 rows.

## 3. Outcome-blind boundary

Only these tables were exported:

- `collector_state`
- `raw_alerts`
- `raw_alert_annotations`
- `collection_runs`

The following tables were present but explicitly not read or exported:

- `episodes`
- `episode_events`
- `episode_build_anomalies`
- `episode_build_runs`
- `mt5_alignment`
- `feature_snapshots`
- `virtual_entries`
- `outcomes`

The package records `outcomes_opened=false`, `outcome_tables_read=false`, `performance_interpretation_performed=false`, and `candidate_formula_designed=false`. No WR, PF, DD, MFE, MAE or trade-result analysis was performed.

## 4. Source timing inventory

The four source/provenance times are available per event:

- `bar_time_utc`: source decision candle time
- `fired_at_utc`: alert firing time
- `received_at_utc`: Worker receipt time
- `downloaded_at_utc`: local Collector fetch/store time

For M7C comparison rows `64–188`, `source_decision_time_utc` equals `bar_time_utc` in all `125 / 125` rows.

The initial Collector catch-up causes large download delays in early IDs and must not be mixed with live latency. Three rows have `downloaded_at_utc` less than `received_at_utc` by less than one second because Collector time is stored to whole-second precision while Worker receipt time has milliseconds. No negative `downloaded_at_utc - fired_at_utc` value exists.

## 5. Annotation

Exactly one event is annotated:

- raw ID `1`
- annotation: `CONNECTION_TEST`
- confirmed by: `USER`

It is excluded from state seeding and research samples.

## 6. Runtime observation nuance

The main SQLite file size and mtime were unchanged before and after BCR01. WAL/SHM sidecars were absent before and present afterward. Collector remained live concurrently, so the sidecar appearance cannot be attributed uniquely to BCR01 and is not evidence of logical row mutation.

Accepted statement:

`NO_LOGICAL_SOURCE_DATABASE_MUTATION_EVIDENCE; LIVE_SQLITE_SIDECAR_ACTIVITY_OBSERVED`

## 7. Decision

BCR01 v1.0.1 is accepted as the immutable outcome-blind source/provenance snapshot for raw IDs `1–194`. The invalid v1.0.0 error package remains audit history only.
