# GML1 live research challenger BAT loop

Date: 2026-06-28  
Mode: audit-only / closed-bar prospective monitoring

## Purpose

This runtime continuously reads the MT5 `goldsharp_*` CSV files from a persistent BAT window. Windows Task Scheduler is not used.

The live-capable sleeves are:

| Component | Candidate | Direction | Source / higher timeframe |
|---|---|---|---|
| A_CORE | GML1-WATCH-022-C | LONG | M15 / H4 |
| B_STATE | GML1-H1D1-STATEFUL-REENTRY24-C | LONG | H1 / D1 |
| P18 | GML1-PROV-018-APPROX | LONG | M15 / H4 |
| W024A | GML1-WATCH-024-A | SHORT | M15 / H4 |

P16 and P19 are explicitly disabled for live decisions because their candidate-specific ML gates are unavailable for new observations.

## Input contract

The runtime searches MT5 terminal folders for a single `MQL5\Files` directory containing all six files:

```text
goldsharp_m1.csv
goldsharp_m5.csv
goldsharp_m15.csv
goldsharp_h1.csv
goldsharp_h4.csv
goldsharp_d1.csv
```

The latest CSV row is treated as closed under the exporter contract. The runtime does not remove the latest valid row based on wall-clock time.

Input is rejected or deferred when:

- a required file is missing;
- timestamps are duplicated or not monotonic;
- an invalid row occurs before the trailing edge;
- a file changes while the six CSVs are being read;
- the exact M1 entry row for a new decision is not available yet.

A trailing incomplete row can be ignored temporarily. A file mutation or missing exact M1 entry row produces `DEFERRED`; the BAT loop retries on the next iteration without advancing state.

## Start

After pulling `main`, double-click:

```text
scripts\gold_ml_v1\live_research_challenger\run_live_loop.bat
```

Default interval:

```text
60 seconds
```

To change it for the current command window:

```bat
set GML1_LIVE_INTERVAL_SECONDS=30
scripts\gold_ml_v1\live_research_challenger\run_live_loop.bat
```

The intended operating interval is 60 seconds. Shorter intervals do not create more closed candles and increase CSV read load.

If multiple MT5 terminals contain all six files, set the exact directory first:

```bat
set "GML1_LIVE_DIR=C:\Users\<user>\AppData\Roaming\MetaQuotes\Terminal\<terminal-id>\MQL5\Files"
scripts\gold_ml_v1\live_research_challenger\run_live_loop.bat
```

## First run

The first run returns:

```text
INITIALIZED_NO_BACKFILL
```

It does not emit old candidates. It reconstructs only the recent state required for:

- currently open parent positions;
- one-position suppression;
- B_STATE's 24-hour re-entry timer.

Subsequent iterations process only source bars newer than `live_state.json:last_processed`.

## Stop

Do not close the loop window as the normal stop method. In another window, double-click:

```text
scripts\gold_ml_v1\live_research_challenger\stop_live_loop.bat
```

The loop stops after the current one-shot run or sleep interval and removes its loop lock.

If Windows or the console was terminated unexpectedly and no loop is actually running, use:

```text
scripts\gold_ml_v1\live_research_challenger\reset_live_loop_lock.bat
```

Do not run the reset command while a live loop is active.

## One-shot diagnostic run

To inspect one pass without starting the persistent loop, double-click:

```text
scripts\gold_ml_v1\live_research_challenger\run_live_once.bat
```

The window remains open and displays the one-shot log.

## Output

```text
outputs\gold_ml_v1\live_research_challenger\
  live_state.json
  live_candidates.csv
  live_candidates.jsonl
  live_audit.jsonl
  latest_status.json
  live_loop.log
  live_loop.previous.log
  run_live_once_last.log
```

`live_candidates.csv` is the current candidate registry. Candidate keys are unique by candidate ID and decision close time. Open records are updated as new M1 closed bars resolve TP, SL or TIME.

`live_state.json` stores:

- M15 and H1 processing cursors;
- B_STATE pending re-entry due time and origin;
- open parent positions by sleeve;
- disabled execution controls.

Deleting `live_state.json` causes a new no-backfill initialization. Do not delete it during normal operation.

## Position contract

- one open parent position per sleeve;
- same-M1 TP/SL collision uses SL priority;
- A_CORE: LONG, TP 1R, SL 1R, 6 hours;
- B_STATE: LONG, TP 1R, SL 1R, 48 hours;
- P18: LONG, TP 1R, SL 1R, 12 hours;
- W024A: SHORT, TP 1.5R, SL 1R, 6 hours;
- SHORT TP/SL/TIME evaluation uses the historical bid/ask spread contract.

Because the input CSV contains closed M1 bars only, a new M15/H1 decision can be deferred until its exact M1 entry row appears. This normally means the candidate is confirmed on a later BAT iteration rather than guessing the entry price.

## Loop behavior

- only one BAT loop may run;
- every loop calls one isolated Python pass;
- a one-shot exception does not terminate the persistent loop;
- `DEFERRED` and `BUSY` are logged separately from hard failures;
- `live_loop.log` rotates at 5 MiB to `live_loop.previous.log`;
- the interval can be set with `GML1_LIVE_INTERVAL_SECONDS`;
- the rotation threshold can be set with `GML1_LIVE_LOOP_MAX_LOG_BYTES`.

## Safety controls

```text
audit_only   = true
final_signal = false
discord      = false
mt5_order    = false
p16_live     = false
p19_live     = false
```

This stage records prospective candle judgments and their M1 outcomes. It does not send Discord notifications and does not place orders.
