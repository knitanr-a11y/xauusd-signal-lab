# BTC BCR02 — canonical source event ledger

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30`
- stage: `BCR02_CANONICAL_SOURCE_EVENT_LEDGER`
- result: `READY_CANONICAL_SOURCE_EVENT_LEDGER_OUTCOME_BLIND`

## 1. Purpose

Convert the accepted BCR01 raw source snapshot into a deterministic state-aware source event ledger before any candle feature or profitability outcome is opened.

This stage separates raw TradingView events into source state before/after, primary alerts, reentries, opposite alerts ignored, valid exits, and opposite exits ignored. No candidate formula or profitability interpretation is performed.

## 2. Frozen inputs

BCR01 package:

- SHA256: `bc562948ee8baefba32d0e291a54341243da4684bdbf43d652676d5fcdab5611`
- snapshot: `BCR01_20260730T030649Z_RAWMAX194`
- raw IDs: `1–194`

M7C D1 package used only for parity validation:

- SHA256: `870ea28c530f1db603afb190a0daa84963b6c7c3d4142ca0859dce1ddb655295`
- comparison IDs: `64–188`
- comparison rows: `125`

Prospective start: `2026-07-20T14:54:15Z`

## 3. State seeding

Raw ID `1` is the user-confirmed connection test and is excluded.

The source state machine is seeded from all remaining pre-prospective raw events. Research scope:

- raw IDs: `64–194`
- rows: `131`
- BTCUSD: `76`
- XAUUSD: `55`

## 4. State machine

### IDLE

- LONG → `PRIMARY_LONG`, role `PRIMARY_ALERT`, state `ACTIVE_LONG`
- SHORT → `PRIMARY_SHORT`, role `PRIMARY_ALERT`, state `ACTIVE_SHORT`

### ACTIVE_LONG

- LONG → `REENTRY_LONG`, role `REENTRY_ALERT`, state unchanged
- SHORT → `OPPOSITE_ALERT_IGNORED`, state unchanged
- LONG_EXIT → `LONG_EXIT`, role `EXIT_ALERT`, state `IDLE`
- SHORT_EXIT → `OPPOSITE_EXIT_IGNORED`, state unchanged

### ACTIVE_SHORT

- SHORT → `REENTRY_SHORT`, role `REENTRY_ALERT`, state unchanged
- LONG → `OPPOSITE_ALERT_IGNORED`, state unchanged
- SHORT_EXIT → `SHORT_EXIT`, role `EXIT_ALERT`, state `IDLE`
- LONG_EXIT → `OPPOSITE_EXIT_IGNORED`, state unchanged

## 5. M7C parity

The deterministic replay was compared against every M7C source comparison row for raw IDs `64–188`.

Exact parity:

- ticker: `125 / 125`
- decision time (`bar_time_utc`): `125 / 125`
- source state before: `125 / 125`
- source transition: `125 / 125`
- source state after: `125 / 125`
- event role: `125 / 125`

Total mismatches: `0`.

This proves state reconstruction parity. It does not prove profitability.

## 6. Research ledger counts through raw ID 194

Transitions:

- `PRIMARY_LONG`: 25
- `PRIMARY_SHORT`: 21
- `LONG_EXIT`: 26
- `SHORT_EXIT`: 20
- `REENTRY_LONG`: 13
- `REENTRY_SHORT`: 10
- `OPPOSITE_ALERT_IGNORED`: 9
- `OPPOSITE_EXIT_IGNORED`: 7

M7C-v1 supported source events are primary alerts and valid exits:

- BTCUSD supported: `53`
- XAUUSD supported: `39`
- total supported: `92`

BTCUSD has `76` total raw events after the prospective start. Unsupported BTC rows are retained as separate event classes; they are not discarded.

## 7. Outcome boundary

- outcomes opened: false
- performance interpretation: false
- candidate formula designed: false
- no WR/PF/DD/MFE/MAE
- no event removed because of a later result

## 8. Next research gate

The next stage is:

`BCR03_BTC_SOURCE_TO_MT5_CANDLE_MAPPING_AND_FEATURE_AVAILABILITY_AUDIT`

Before trigger hypotheses are proposed, BCR03 must prove:

- exact BTC M15 candle source path and SHA
- TradingView/VANTAGE `bar_time_utc` to MT5 server-open mapping
- source alert price versus MT5 bar price relationship
- closed-bar availability at decision time
- explicit gap handling
- exact feature availability without current-bar high/low/close
