# GML1 live log retention

Date: 2026-06-29

## Operating mode

While `run_live_loop.bat` is running, Discord delivery and the MT5 execution adapter are treated as continuously enabled. Legacy false values for the old enable keys do not turn off a complete configuration.

A missing or invalid `.env` prevents new entries. Existing open positions remain subject to the recovery and management path.

Dry-run versus real-order mode remains a separate safety setting. The repository does not silently change dry-run into real-order mode.

## Short-retention logs

Discord delivery logs and runtime logs are stored by date:

```text
logs/notifications/YYYY/MM/discord_YYYY-MM-DD.jsonl
logs/runtime/YYYY/MM/
```

They are compressed after 7 days and deleted after 31 days.

The current loop log rotates at 5 MiB into the dated runtime folder. `run_live_once_last.log` and `latest_status.json` remain overwrite-only files.

## Permanent trade records

Closed real MT5 positions are kept permanently by month:

```text
trades/YYYY/live_trades_YYYY-MM.csv
```

Search and reporting files:

```text
trades/trade_index.csv
trades/monthly_summary.csv
```

`trade_index.csv` is the all-time searchable list. `monthly_summary.csv` contains month and sleeve totals, wins, win rate and net profit.

The operational file `live_execution_ledger.csv` is kept small. It retains rows still needed for open-position management, notification retry or recent non-trade diagnostics. Once a closed real position has been recorded and its exit notification is complete, the row is moved into the permanent monthly archive.

All candidate keys are retained separately in:

```text
state/candidate_key_index.csv
```

This prevents an archived candidate from being processed again after its operational row has been removed.

Live win-rate calculations combine the operational ledger with the permanent trade index, so monthly archiving does not reset or shorten the displayed live win rate.

The latest maintenance result is written to:

```text
log_manifest.json
```

## Remaining operational risks

- The BAT loop is not automatically relaunched after a Windows reboot, logout, closed console or unexpected process termination unless a scheduler or watchdog is installed on the user PC.
- Permanent files on the same local disk do not protect against disk failure, theft or filesystem loss. An external backup destination is still required.
- The permanent row is position-level. It stores the important tickets, prices, result and aggregate net profit, but it is not yet a full immutable copy of every individual broker deal row.
- An MT5 fill can succeed before a Discord request fails. The notification remains unsent in the operational ledger and is retried, but the position may temporarily exist without a Discord message.
