# BTC D1 — M7C一次証拠パッケージ監査

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T06:49:00+09:00`
- stage: `D1_M7C_COLLECTOR_SOURCE_INVENTORY_READ_ONLY`
- result: `M7C_PRIMARY_EVIDENCE_ACCEPTED_COLLECTOR_PROVENANCE_PENDING`
- scope: schema / timestamp / event provenance / state semantics / outcome exposure only
- performance interpretation: forbidden and not performed

## 1. User package

User upload:

`新しい圧縮された (ZIP) フォルダー.zip`

ZIP SHA256:

`870ea28c530f1db603afb190a0daa84963b6c7c3d4142ca0859dce1ddb655295`

ZIP size:

`299121 bytes`

Expected seven M7C files were all present. One useful additional file was also present:

`m7c_runtime_start_receipt.json`

The package is accepted as a manual D1 inspection package. It is not yet an immutable D2 snapshot because the runtime was active while the files were copied and no before/after source hash proof was captured.

## 2. Exact file manifest

| file | bytes | SHA256 |
|---|---:|---|
| `latest_m7c_extra_proxy_signals.csv` | 13636 | `557966083e0b702babedfe8ceaa430f19db08b4e73fd58bae67ab8dd6059e69f` |
| `latest_m7c_prospective_shadow.json` | 10689 | `a45f74f450aac8d4032e7f5629866da04206bc3c57490352c42bf4d946f41cac` |
| `latest_m7c_proxy_decisions.csv` | 312741 | `865875cb21f545ef054cc97835f758c3b04145f8cd4e752005fbd46d66eb84f4` |
| `latest_m7c_proxy_signals.csv` | 21001 | `e27a7b5459718a849766f2db2aebe0d38211a11ebd9cd02385238f111a386fed` |
| `latest_m7c_shadow_loop_status.json` | 1147 | `dcfd72fe109a73eee25c1bc0299f926c453de0337d0eb7ef47a1293c7587aaf0` |
| `latest_m7c_source_event_comparisons.csv` | 15259 | `5e4a2e348e83558d6889bfbfecdf35e874dac6a705402be8f572bcd36ff5a93d` |
| `m7c_runtime_start_receipt.json` | 2461 | `55e525b02c7729c92c2b6c73f2cf42c75ea14b430664f1bf99e890f4d0cd029d` |
| `m7c_shadow_forever.log` | 6445524 | `d994a389c1198f133f0198cdd9abe14669ca40fab14f8fe2f32cae6d9515ece8` |

Archive timestamps for the live report files were clustered at approximately `2026-07-30 06:46:22–06:46:24 JST`. The runtime start receipt retained its original `2026-07-20 23:54:16 JST` file timestamp.

## 3. Runtime and safety state

`latest_m7c_prospective_shadow.json` reports:

- status: `COLLECTING`
- stage: `M7C_PROSPECTIVE_SHADOW_REPRODUCTION_AUDIT_ONLY`
- contract: `MOCHIPOYO_M7C_PROSPECTIVE_SHADOW_V1`
- built at: `2026-07-29T21:46:15Z`
- prospective start: `2026-07-20T14:54:15Z`
- closed M15 features only: true
- current M15 open only: true
- current high/low/close used: false
- future fields used: false
- trade outcome fields used: false
- formula refit performed: false
- historical pre-start decisions scored: false
- reentry rule used: false
- audit-only: true
- Discord / MT5 / live_ready / final_signal / entry gate: all false

`latest_m7c_shadow_loop_status.json` reports:

- status: `RUNNING`
- current process start: `2026-07-23T06:36:43Z`
- cycles: `1884`
- successful cycles: `1884`
- failed cycles: `0`
- last exit code: `0`
- interval: `300 seconds`

No runtime or source files were modified by this BTC audit.

## 4. Schema inventory

### 4.1 `latest_m7c_source_event_comparisons.csv`

Rows: `125`

Columns:

- `raw_alert_id`
- `ticker`
- `source_decision_time_utc`
- `source_transition`
- `source_state_before`
- `source_state_after`
- `event_role`
- `classification`
- `proxy_decision_time_utc`
- `proxy_transition`
- `proxy_kernel_id`
- `bar_delta`

This file carries source/proxy transition matching evidence. It does not carry source price, raw message payload, collection timestamp or trading outcome fields.

### 4.2 `latest_m7c_proxy_decisions.csv`

Rows: `1557`

Columns:

- `ticker`
- `decision_time_utc`
- `selected_server_open`
- `current_server_open`
- `state_before`
- `emitted_transition`
- `kernel_id`
- `state_after`
- `ambiguous_primary_conflict`
- `rci9`
- `rci9_delta1`
- `rci9_turn_up`
- `rci9_turn_down`
- `ema_alignment`
- `ema20_minus_ema30_bps`
- `ema30_minus_ema40_bps`

### 4.3 `latest_m7c_proxy_signals.csv`

Rows: `168`

Columns:

- `ticker`
- `proxy_decision_time_utc`
- `proxy_transition`
- `proxy_kernel_id`
- `state_before`
- `state_after`
- `rci9`
- `rci9_delta1`
- `rci9_turn_up`
- `rci9_turn_down`
- `ema_alignment`

### 4.4 `latest_m7c_extra_proxy_signals.csv`

Rows: `104`

Columns:

- `ticker`
- `proxy_decision_time_utc`
- `proxy_transition`
- `proxy_kernel_id`
- `proxy_state_before`
- `proxy_state_after`
- `classification`
- `source_arrival_grace_minutes`
- `rci9`
- `ema_alignment`

Every row is classified as `FINALIZED_EXTRA_PROXY_SIGNAL`. These are signal transitions, not automatically 104 independent completed trades.

## 5. Event inventory

The source comparison ledger contains contiguous, unique raw alert IDs `64` through `188`.

- rows: `125`
- duplicate raw IDs: `0`
- missing IDs within 64–188: `0`
- source-time regression when sorted by raw ID: `0`
- full-row duplicates: `0`

All summary counts in the JSON agree with the CSV ledgers.

### 5.1 Source event classes

- supported and scored: `90`
- unsupported REENTRY: `23`
- unsupported opposite events: `12`
- total source comparison rows: `125`

Supported source events by ticker:

- BTCUSD: `51`
- XAUUSD: `39`

Supported source events by transition:

- `PRIMARY_LONG`: `25`
- `PRIMARY_SHORT`: `20`
- `LONG_EXIT`: `26`
- `SHORT_EXIT`: `19`

Unsupported transitions:

- `REENTRY_LONG`: `13`
- `REENTRY_SHORT`: `10`
- `OPPOSITE_ALERT_IGNORED`: `7`
- `OPPOSITE_EXIT_IGNORED`: `5`

### 5.2 Source-fidelity classes

- exact match: `55`
- one M15 bar late match: `9`
- supported missed source: `26`
- wrong transition nearby: `0`

Within-one-bar matched proxy keys are one-to-one; no matched proxy key was reused.

These are reproduction/fidelity counts, not trading profitability evidence.

### 5.3 Proxy transitions

Proxy decisions:

- BTCUSD: `890`
- XAUUSD: `667`
- total: `1557`

Emitted proxy signals:

- `PRIMARY_LONG`: `43`
- `PRIMARY_SHORT`: `41`
- `LONG_EXIT`: `44`
- `SHORT_EXIT`: `40`
- total: `168`

Every signal row joined exactly to one non-`NO_SIGNAL` decision with identical transition and kernel. There were no orphan signal rows.

Finalized extra proxy transitions:

- BTCUSD: `52`
- XAUUSD: `52`
- total: `104`

## 6. State and formula evidence

The frozen M7C manifest records:

- `PRIMARY_LONG`: `IDLE` + `rci9_turn_up` + `BULLISH_STACK`
- `PRIMARY_SHORT`: `IDLE` + `rci9_turn_down` + `BEARISH_STACK`
- `LONG_EXIT`: `ACTIVE_LONG` + `rci9 >= 78.333333333333`
- `SHORT_EXIT`: `ACTIVE_SHORT` + `rci9 <= -75`
- REENTRY: not modeled or scored
- opposite primary while active: not evaluated
- simultaneous primary conflict: fail-safe `NO_SIGNAL`

Causality contract:

- timeframe: M15
- decision: new M15 bar open
- indicators: immediately previous fully closed M15 bar
- current bar field allowed: open only
- current high/low/close forbidden
- future bars forbidden
- trade outcomes forbidden

This is M7C fidelity evidence. It is not yet the BTC candidate formula to be adopted.

## 7. Clock-domain inventory

All `1557` proxy decisions satisfy:

`decision_time_utc = current_server_open - 3 hours`

The package therefore consistently represents the observed MT5 server wall clock as UTC+3 for this interval.

For `1549 / 1557` rows:

`current_server_open - selected_server_open = 15 minutes`

Eight gap rows were present:

- six XAUUSD daily rollover gaps of `75 minutes`
- one XAUUSD weekend gap of `2955 minutes`
- one BTCUSD gap of `30 minutes`

All eight emitted `NO_SIGNAL`. They must remain explicit gaps; they must not be silently interpolated.

`source_decision_time_utc` and `proxy_decision_time_utc` are explicit UTC fields. However, the package does not expose the Collector receipt timestamp or raw source payload timestamp semantics. Therefore D1 cannot yet prove whether the genuine source time is publication time, signal candle time, upstream event time, or a normalized decision time.

## 8. Log continuity observation

The log contains `2503` successful cycle headers and no nonzero exit, traceback, error or failed cycle text.

Cycle numbering appears in two runs:

- first run: cycles `1–619`
- second/current run: cycles `1–1884`, starting `2026-07-23T06:36:43Z`

The prospective start remained `2026-07-20T14:54:15Z`; it was not reset.

The exact read-only forced-reboot contract states that after a forced reboot, stale locks may be removed and persistent loops restarted without deleting the runtime manifest, prospective start or SQLite state. The observed reset is compatible with that recovery design, but this package does not contain the actual recovery-run receipt. It is therefore recorded as `COMPATIBLE_WITH_FORCED_REBOOT_RECOVERY_NOT_YET_PROVEN` rather than silently treated as uninterrupted operation.

## 9. Outcome-exposure inventory

The inspected CSV schemas contain no columns for:

- win/loss
- TP/SL
- P/L
- R
- PF
- DD
- MFE
- MAE
- future high/low/close

The report explicitly states `trade_outcome_fields_used=false` and `future_fields_used=false`.

Accordingly, the eight submitted files are accepted as pre-outcome structural/fidelity evidence for D1. No WR, PF, DD, MFE or MAE analysis was performed.

Caution:

- source-fidelity counts such as exact recall are visible and therefore exposed for future reproduction research;
- they are not trading outcomes;
- any later formula modification intended to improve fidelity must use a separately frozen evaluation design;
- any later profitability gate must not be tuned on the same sample used to claim its performance.

## 10. D1 findings accepted

Accepted:

- exact M7C file names and schemas
- M7C status and frozen prospective start
- event classes and state transitions
- 125 contiguous post-start raw event IDs
- 90 supported source events, including 51 BTCUSD events
- proxy decision and signal ledgers
- UTC / MT5 server UTC+3 mapping for the observed interval
- causal feature-use contract
- no outcome fields in the submitted artifacts

## 11. Remaining D1 blockers

The following cannot be established from the submitted package:

1. Collector current status, cycle count, failures and cursor progression.
2. Exact genuine source raw payload and its immutable identifier beyond `raw_alert_id`.
3. Collector receipt/collection timestamp.
4. Duplicate, revision, replacement and late-arrival behavior at the Collector layer.
5. Meaning of the genuine source event timestamp before M7C normalization.
6. Source platform BTCUSD symbol/price source and its mapping to the existing MT5 BTC candle source.
7. Exact recovery-run evidence for the 2026-07-23 process restart.
8. Whether the Collector storage contains any outcome-like or post-event fields that must be quarantined.

## 12. Next action

Continue D1 in read-only mode with the existing Collector evidence files:

- `collector_forever.log`
- `latest_loop_status.json`
- `latest_collection_result.json`

Place these exact existing files into one ZIP without stopping, restarting or editing Collector/M7C.

If the files reference a SQLite/database path, do not send or modify the database yet. First inventory the three files; then define the exact minimal read-only snapshot needed for raw event provenance.

No candidate formula, performance evaluation, new BAT, FF06, shadow or live action is authorized yet.
