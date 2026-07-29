# BCR01 — Outcome-blind Collector source snapshot contract

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30`
- user-facing stage: `BCR01_outcome_blind_source_snapshot`
- status: `IMPLEMENTED_READY_FOR_ONE_LOCAL_RUN`

## Purpose

Create one immutable logical snapshot of genuine Mochipoyo source/provenance records needed for BTC research, without stopping or modifying Collector/M7C and without opening outcome-bearing tables.

## Input

Exact default source:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\mochipoyo_alerts.sqlite3`

No source discovery, filename fallback, raw database copy, WAL copy or SHM copy is permitted.

## SQLite access contract

- open with SQLite URI `mode=ro`;
- enable `PRAGMA query_only=ON`;
- use one consistent read transaction;
- do not stop or restart Collector;
- do not execute INSERT, UPDATE, DELETE, CREATE, DROP, VACUUM or migration;
- live DB/WAL/SHM files may continue changing after the read transaction begins;
- logical transaction consistency, not whole-file SHA, defines the snapshot.

## Allowlisted tables

Only these tables may be queried and exported:

1. `collector_state`
2. `raw_alerts`
3. `raw_alert_annotations`
4. `collection_runs`

Their exact column order is frozen in the BCR01 script. Missing, reordered or unexpected columns fail closed.

## Forbidden tables

The following are not queried or exported:

- `episodes`
- `episode_events`
- `episode_build_anomalies`
- `episode_build_runs`
- `mt5_alignment`
- `feature_snapshots`
- `virtual_entries`
- `outcomes`

The full SQLite database must not be uploaded.

## Integrity checks

Before accepting the snapshot:

- `last_successful_id == max(raw_alerts.cloudflare_id)`;
- raw alert IDs are unique;
- event keys are unique;
- canonical `collector_source_row_json` SHA256 equals stored `payload_sha256`;
- source JSON identity matches stored ID, event, ticker and timestamps;
- annotations reference existing raw alert IDs;
- collection run IDs are unique;
- Cloudflare collection cursor does not regress;
- status values are valid;
- forbidden tables exported = zero.

Failure stops once and creates an error ZIP. There is no retry loop.

## Outputs

`%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\BCR01_outcome_blind_source_snapshot\LATEST\`

- `00_READ_ME_FIRST.txt`
- `01_snapshot_summary.json`
- `02_source_schema_manifest.json`
- `03_collector_state.csv`
- `04_raw_alerts_manifest.csv`
- `05_raw_alerts_payloads.jsonl`
- `06_raw_alert_annotations.csv`
- `07_collection_runs.csv`
- `08_integrity_checks.json`
- `09_runtime_file_observation.json`
- `99_UPLOAD_PACKAGE.zip`

## Safety

- audit-only;
- no candidate formula;
- no WR/PF/DD/MFE/MAE interpretation;
- no Discord;
- no MT5 orders;
- no live-ready or automatic promotion;
- no write to GOLD/MOCHIPOYO paths except SQLite's own existing Collector process continuing independently;
- BCR01 itself writes only under the BTC output root.

## Stop

After one BAT run, upload `99_UPLOAD_PACKAGE.zip` and stop. BCR02 or candidate grammar is not automatically authorized by BCR01 completion.
