# BTC FF01 fresh-forward availability audit contract

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative base branch: `main`
- working branch: `feature/btc-fresh-forward-research`
- stage: `BTC_FF01_FRESH_FORWARD_DATA_AVAILABILITY_AUDIT_READ_ONLY`
- cutoff: `entry_dt > 2026-07-02 02:15:00 UTC`

## 1. Purpose

FF01 checks only whether the frozen five BTC ML V1 candidates have sufficient current closed-bar inputs for a later fresh-forward evaluation.

FF01 does not generate candidate trades and does not calculate fresh performance.

Frozen candidates:

- `BTC4_RISK_CAP_400`
- `BTC5_TWO_PIVOT_P2_CLEAN_N_382_786`
- `BTC6_M15_TWO_PIVOT_P3_BROAD_N_236_886`
- `BTC7R_M15_IMPULSE_HIGH_WIN_24_96_M22_R110`
- `BTC9R_M15_PREVDAY_BREAKOUT_HIGH_WIN_R080`

## 2. Historical H4 correction

`BTCUSD_H4_WARMUP_PACKAGE.zip` and its 2017-start `btcusdsharp_h4.csv` were used only to completely reproduce historical BTC4 results.

That historical package is not a current MT5 fresh-tail input and is not required for fresh-forward readiness.

The user does not need to locate, restore or recreate that package for FF01.

## 3. Dual-track separation

Track A is BTC ML V1 frozen-five research on `feature/btc-fresh-forward-research`.

Track B is the running M7C genuine-source prospective background track on `feature/mochipoyo-alert-research` for `BTCUSD` and `XAUUSD`, with immutable start `2026-07-20T14:54:15Z`.

FF01 must not:

- read M7C runtime output as an FF01 input
- modify M7C formula, matching, start, runtime, state, lock or review gate
- stop, restart or taskkill collector, M7C, M8C or GOLD loops
- merge `feature/mochipoyo-alert-research` into the BTC working branch
- touch M10W24B or any other M10W stage
- broaden the GOLD-only M10 line to BTC

## 4. User-facing layout

```text
scripts/btc_ml_v1/fresh_forward_availability/
  python/
    audit_btc_fresh_forward_availability.py

  bat/
    00_READ_ME_FIRST.txt
    01_run_availability_audit.bat
    02_open_latest_results.bat
```

The user runs BAT files only.

`01_run_availability_audit.bat` runs the audit once, opens `LATEST` after execution and keeps the command window open for review.

`02_open_latest_results.bat` only reopens the existing `LATEST` folder. It does not rerun the audit.

## 5. Allowed input discovery

The auditor may inspect only:

- repository `Files`
- the exact known BTC MT5 terminal Files path already used by the main BTC support code
- `C:\BTC_REPRO\history`
- explicit paths supplied through the numbered BAT

No whole-PC recursive search is allowed.

Only `btcusdsharp` BTC files are eligible. A similar filename, another symbol or an unrelated CSV must not be substituted.

## 6. Time contract

- CSV `time` is the bar-open timestamp.
- The latest CSV row is closed by contract.
- A naive MT5 timestamp is broker-server wall-clock time, not UTC.
- FF01 reuses broker UTC offset inference and conversion functions from `scripts/run_btc_youtube_candidates_dry_run_cycle.py`.
- FF01 does not independently subtract a fixed two or three hours.
- Post-cutoff rows are counted strictly with UTC-converted bar-open timestamp greater than `2026-07-02 02:15:00`.

## 7. Required timeframe audit

FF01 checks current fresh tails for:

- M5
- M15
- H1
- D1
- H4

For each inspected file, the report records:

- actual path
- file size
- row count
- first raw MT5 broker-server timestamp
- latest raw closed-bar timestamp
- timestamp timezone state
- selected broker UTC offset
- offset inference evidence
- latest UTC-converted closed-bar timestamp
- rows strictly after the cutoff
- non-ascending timestamp count
- duplicate timestamp count
- read error or ambiguity

A source containing non-ascending or duplicate timestamps is not READY.

## 8. Candidate-specific readiness

Each candidate is classified independently.

- BTC4: H4 after cutoff + M5 after cutoff
- BTC5: M5 after cutoff
- BTC6: M15 after cutoff
- BTC7R: M5 + M15 + H1 after cutoff
- BTC9R: M5 + M15 + H1 + D1 after cutoff

A missing D1 file may block BTC9R, but it must not block BTC4, BTC5, BTC6 or BTC7R when their own requirements are satisfied.

## 9. Output contract

```text
%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability\
  LATEST\
    00_READ_ME_FIRST.txt
    01_availability_summary.json
    02_availability_report.txt
    99_UPLOAD_PACKAGE.zip

  archive\
    <UTC execution timestamp>\
```

The ZIP contains only the readme, JSON summary and text report. Raw candle CSV files are never included.

## 10. Hard safety gates

FF01 must not:

- append, overwrite, copy, merge, rename, truncate or delete source CSV files
- run a candidate engine
- generate fresh trades
- implement or run a fresh performance evaluator
- run `reproduce_btc_stacking_portfolio.py` against extended fresh CSV files
- use `--skip-input-hash-check` as a fresh evaluator
- change candidate conditions, thresholds, TP, SL, exit order, spread, pip or overlap rules
- design lots or monetary DD
- add BTC10R or search for a new candidate
- create a collector, resident loop or dashboard
- send Discord messages
- send MT5 orders
- enable `live_ready` or `final_signal`

## 11. Stop condition

Stop after `99_UPLOAD_PACKAGE.zip` or a clear BLOCKED package has been produced.

The package must be reviewed by the user before any FF02 design or execution. FF02 remains unauthorized.
