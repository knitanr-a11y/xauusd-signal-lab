# GML1 autotrade connected

Date: 2026-06-29

## Entry point

Use the repository-root launcher:

```text
RUN_GML1_AUTOTRADE.bat
```

It starts:

```text
scripts/gold_ml_v1/live_research_challenger/run_live_autotrade_loop.bat
```

The loop uses the connected one-shot path and the complete MT5 deal archive layer. It shares the existing `live_loop.lock`, so it cannot run beside the older live loop.

## Execution controls

The order path remains fail-closed. A new order is possible only when `MT5 MQL5/Files/.env` contains a valid Discord webhook, the broker's exact symbol, positive sleeve volume, real-order mode, and the exact confirmation token. No symbol or volume is guessed.

The connected path retains the existing controls for stale candidates, one position per sleeve, total position count, broker volume step, minimum stop distance, filling mode, deterministic magic/comment identity, SL/TP, horizon exit, and open-position recovery.

## Complete deal retention

Every closed MT5 position must have a complete deal snapshot before its position row can leave the operational ledger.

Permanent deal files:

```text
outputs/gold_ml_v1/live_research_challenger/
  trades/deals/YYYY/mt5_deals_YYYY-MM.csv
  trades/deal_position_index.csv
  trades/deal_archive_status.json
```

Each deal row contains the candidate identity, position ticket, deal ticket, order ticket, millisecond timestamp, UTC timestamp, deal type, entry type, reason, magic, symbol, volume, price, commission, swap, profit, fee, comment, external ID, capture time, and SHA-256 row hash.

The position index stores deal counts, entry/exit counts, first and last deal time, deal-derived net profit, ledger net profit, their difference, archive files, and a position digest.

A position is not marked complete when:

- no closing deal exists;
- deal tickets are duplicated;
- multiple position IDs are mixed;
- the deal-derived net result differs from the position ledger result beyond the tolerance;
- a previously stored deal ticket or position digest changes.

Incomplete positions stay in `live_execution_ledger.csv` for retry and are not moved into the monthly position archive.

## Time basis

Raw MT5 `time_msc` is retained. The readable deal timestamp and monthly deal partition are generated in UTC from `time_msc`, avoiding Windows regional-time and month-boundary drift.

## Validation

The deal archive contract verifies compilation, complete deal persistence, SHA-256 hashes, position indexing, UTC normalization, and rejection of aggregate/deal net mismatches. Existing GOLD_ML_V1 execution, supervisor, live-only win-rate, always-on, and log-lifecycle tests remain applicable.

Actual broker execution still requires the user's Windows MT5 terminal and cannot be performed by GitHub Actions.
