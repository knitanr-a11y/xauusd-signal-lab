# GML1 live notification improvement and BTC reuse handoff

Date: 2026-07-02
Repository: `knitanr-a11y/xauusd-signal-lab`
Base branch: `main`

## 1. Current operational state

PR #69 was merged into `main` as merge commit:

```text
ab8dfcfd2e03a626385a540bc523478f11a51c73
```

The live GOLD system currently covers four sleeves:

- `A_CORE / GML1-WATCH-022-C`
- `B_STATE / GML1-H1D1-STATEFUL-REENTRY24-C`
- `P18 / GML1-PROV-018-APPROX`
- `W024A / GML1-WATCH-024-A`

Current fixed runtime profile:

- MT5 symbol: `GOLD#`
- Volume: `0.01` for all four sleeves
- Recommended launcher:
  `scripts/gold_ml_v1/live_research_challenger/run_live_gold_hash_profile.bat`
- Default total simultaneous GML1 positions: `1`

## 2. User-PC field result reported on 2026-07-02

The user reports that the system was left running for several days and completed one real live cycle:

1. one signal was detected;
2. a real MT5 order was sent;
3. the position hit SL;
4. the signal/order notification arrived;
5. the closing/result notification arrived.

This is user-reported field evidence that the following path worked at least once on the user's PC and broker account:

```text
closed CSV update
→ candidate detection
→ execution ledger registration
→ real MT5 market order
→ server-side SL close
→ closed-position/deal reconciliation
→ Discord entry and exit notifications
```

Do not overstate this as complete production verification. The assistant has not independently inspected the user's local logs, tickets or archive files in this chat.

Still not field-verified across all paths:

- TP closure;
- wall-clock time exit;
- all four sleeves;
- restart recovery with an open position;
- duplicate recovery after a crash;
- partial fills;
- broker rejection/retry paths;
- actual permanent archive contents after this first live trade;
- long-duration Windows restart/watchdog behavior.

## 3. Next task A: improve Discord notification readability

### Current implementation point

The active live-only message formatter is in:

```text
scripts/gold_ml_v1/live_research_challenger/live_execution_live_wr.py
```

Functions:

```text
_entry_message()
_exit_message()
```

The current entry message exposes internal implementation terms directly:

- `GML1 XAUUSD 候補`
- `軸`
- raw candidate ID
- `LONG` / `SHORT`
- raw statuses such as `ORDER_FILLED`
- raw MT5 result text under `注記`

This is the main reason the signal notification is hard to read.

### Important schema limitation

The current execution ledger stores:

- candidate key and candidate ID;
- sleeve/comp;
- direction;
- decision and horizon times;
- execution/trade state;
- symbol and volume;
- order/deal/position tickets;
- fill, SL and TP;
- broker retcode/message;
- close result and net profit;
- notification timestamps.

It does **not** store these useful signal-explanation fields:

- `source_timeframe`;
- `higher_timeframe`;
- `features_json`;
- ATR used at detection;
- target R;
- horizon hours as a separate ledger field;
- a human-readable strategy name;
- a concise reason why the signal qualified.

Therefore there are two distinct notification improvements:

1. **Presentation-only improvement**
   Translate labels and statuses, improve order and spacing, remove internal wording, and show existing price/order information clearly.
2. **Signal-explanation improvement**
   Extend the registry-to-ledger contract so the notification can explain the source timeframe, higher timeframe, strategy condition and risk contract.

Do not pretend that changing only `_entry_message()` can display a genuine detection reason that is not present in the ledger.

### Recommended implementation boundary

Create a separate formatter module instead of adding more hard-coded strings to the execution engine:

```text
scripts/live_common/notification_formatter.py
```

or, as a smaller first step:

```text
scripts/gold_ml_v1/live_research_challenger/live_notification_formatter.py
```

The formatter should accept an asset/profile object containing at least:

```text
system display name
asset display name
broker symbol
strategy/sleeve display-name mapping
direction display mapping
execution-status display mapping
price precision policy
```

Suggested GOLD strategy labels:

```text
A_CORE  → 4時間足環境＋15分足コア
B_STATE → 日足環境＋1時間足ブレイク／再エントリー
P18     → 15分足スクイーズ上抜け
W024A   → 高ボラ反転ショート
```

The labels are presentation names only. They must not alter formulas, thresholds, directions, target R or horizons.

### Suggested readable entry layout

Example structure, not yet implemented:

```text
🟢 GOLD 新規買い注文 約定

戦略      : 15分足スクイーズ上抜け（P18）
判定時刻  : 2026-07-xx xx:xx（MT5サーバー時刻）
銘柄      : GOLD#
ロット    : 0.01

約定価格  : xxxx.xxx
損切り    : xxxx.xxx
利益確定  : xxxx.xxx
保有期限  : 12時間

実運用成績: 0勝1敗 / 勝率0.00%
注文状態  : 約定済み
```

For detection explanation after schema extension:

```text
検出条件  : M15ボリンジャーバンド上抜け＋直前スクイーズ
上位環境  : H4 ATR比1以上・EMA40傾き上向き
```

### Suggested readable exit layout

```text
❌ GOLD 決済：損切り

戦略      : 15分足スクイーズ上抜け（P18）
方向      : 買い
決済理由  : SL
実損益    : -xx.xx（口座通貨）
決済時刻  : 2026-07-xx xx:xx

実運用成績: 0勝1敗 / 勝率0.00%
```

### Compatibility requirement

There is already a real live ledger on the user's PC. Any ledger extension must be backward compatible.

The existing loader currently rejects a ledger when required columns are missing. For additive fields, implement a schema migration/default-fill path rather than requiring the user to delete the live ledger. Never reset or discard:

- candidate history;
- open-position state;
- trade index;
- deal archive;
- live win-rate history;
- sent-notification markers.

### Notification tests required

Add tests for:

- Japanese display mapping for every execution status;
- LONG/SHORT display as 買い/売り;
- entry, dry-run, skipped, error and recovered states;
- SL, TP, time exit and manual close labels;
- missing optional fields;
- old ledger schema migration;
- Discord 2000-character limit;
- no duplicate notification after restart;
- no change to candidate detection or order placement.

## 4. BTC reuse boundary

The BTC system must be a separate signal research and live state. Reuse infrastructure, not GOLD thresholds or historical results.

### A. Safe to reuse almost as-is

These are primarily infrastructure modules:

- `live_discord.py`
  - HTTPS webhook delivery;
  - retry and rate-limit handling.
- `live_store.py`
  - atomic JSON/CSV writes;
  - registry/state helpers, after removing GOLD-specific assumptions if any.
- `live_log_manager.py`
  - notification/runtime log retention;
  - permanent position index and monthly summaries;
  - candidate-key duplicate index.
- `live_deal_archive.py`
- `live_deal_archive_strict.py`
  - immutable MT5 deal rows;
  - deal/ledger reconciliation;
  - UTC normalization;
  - position digest and collision detection.
- `live_execution_deal_safe.py`
  - prevents position compaction before complete deal archive.
- general lock, one-shot and polling concepts;
- live-only win-rate calculation concept.

These should eventually move to an asset-neutral shared package instead of being copied and allowed to diverge.

### B. Reusable only after parameterization

#### `live_settings.py`

Reusable concepts:

- dotenv parsing;
- Discord/MT5 settings;
- symbol, lot, fill mode and connection controls;
- real-order confirmation token;
- max position and entry-lag controls.

Currently GOLD/GML1-coupled through:

- `SLEEVES`;
- `GML1_...` environment-variable names;
- GML1 default magic base;
- GOLD output/history defaults;
- Discord default name.

BTC needs a separate namespace/profile, or a generic settings layer with asset-specific prefixes.

#### `live_mt5.py`

Reusable concepts:

- MT5 initialize/shutdown;
- terminal/account validation;
- symbol selection;
- broker minimum/step volume validation;
- price-digit normalization;
- filling-mode discovery;
- order check/send;
- market close;
- open-position and deal-history recovery;
- closed-position net-profit calculation.

Currently coupled through:

- GML1 sleeve magic offsets;
- GML1 comment codes;
- `gml1_positions()` naming and filters;
- error wording;
- ATR-based SL/TP contract assumed from GOLD candidate records.

Refactor to accept an execution profile containing system ID, magic base, strategy IDs and comment prefixes.

#### `live_execution.py`, `live_execution_supervisor.py`, `live_execution_live_wr.py`

Reusable concepts:

- no-backfill initialization;
- stale-signal rejection;
- one-position-per-strategy;
- total-position cap;
- idempotent execution ledger;
- recovery of missing position tickets;
- horizon close;
- live-only win rate;
- entry/exit notification retry.

Currently coupled through:

- GML1 naming;
- GOLD message text;
- four fixed sleeves;
- candidate record assumptions;
- GOLD output locations;
- hard-coded notification display.

These should consume asset and strategy profiles rather than be copied wholesale.

#### `live_position.py`

The M1 first-touch engine and same-bar SL priority are structurally reusable, but these must become asset-profile inputs:

- point size and spread conversion;
- strategy direction;
- target R;
- horizon;
- entry/exit price convention;
- weekend/session behavior.

Do not reuse the GOLD `CONTRACTS` table as BTC contracts.

#### loop/BAT scripts

Polling, lock and stop-file behavior can be reused, but BTC needs separate:

- launcher;
- lock directory;
- stop file;
- output directory;
- run log;
- state and ledger;
- environment settings/profile.

GOLD and BTC loops must not block or overwrite one another.

### C. Do not reuse as BTC signal logic

The following are GOLD signal research products and must not be treated as BTC strategies:

- `live_proposals_m15.py` formulas and thresholds;
- `live_proposals_h1.py` formulas and thresholds;
- candidate IDs `GML1-WATCH-022-C`, `GML1-H1D1-STATEFUL-REENTRY24-C`, `GML1-PROV-018-APPROX`, `GML1-WATCH-024-A`;
- GOLD directions, target R and horizons in `live_position.CONTRACTS`;
- GOLD historical win rates, candidate counts and validation results;
- `goldsharp_*.csv` filenames;
- GOLD-specific point/spread assumptions;
- `GOLD#` and fixed `0.01` volume;
- GML1 magic numbers and MT5 comments;
- GOLD output/state files.

Although many GOLD features are ATR-normalized, that does not validate their thresholds on BTC. Copying them would be an unvalidated strategy transplant.

## 5. BTC system recommended structure

Keep GOLD operational while BTC is developed independently.

Suggested directories:

```text
scripts/live_common/
  discord.py
  mt5_client.py
  execution_engine.py
  deal_archive.py
  log_manager.py
  notification_formatter.py

scripts/btc_ml_v1/
  research/
  live_research_challenger/
  profiles/

tests/live_common/
tests/btc_ml_v1/

outputs/btc_ml_v1/
```

Do not move operational GOLD files in one large change. Extract common modules incrementally with parity tests so the live GOLD path remains stable.

## 6. BTC work order

### Stage BTC-0: broker and data contract audit

Determine from the user's MT5 environment:

- exact broker symbol, without assuming `BTCUSD`;
- digits and point size;
- contract size;
- minimum volume and volume step;
- typical spread and spread unit;
- allowed fill modes;
- minimum stop distance;
- whether trading is available on weekends;
- actual bar timestamps and MT5 server timezone behavior;
- available M1/M5/M15/H1/H4/D1 history depth.

Do not automatically reuse GOLD `0.01`. BTC contract size differs by broker and can make the same nominal lot much larger or smaller in risk.

### Stage BTC-1: CSV exporter and closed-row parity

Create BTC CSVs with an explicit asset-specific naming contract, for example:

```text
btc_m1.csv
btc_m5.csv
btc_m15.csv
btc_h1.csv
btc_h4.csv
btc_d1.csv
```

The latest CSV row must remain closed by contract. Open/as-of rows must not enter signal decisions.

### Stage BTC-2: historical data audit

Audit:

- gaps and duplicates;
- weekend continuity;
- spread distribution;
- missing/zero tick volume;
- candle synchronization;
- exact first/last timestamps;
- regime coverage;
- M1 availability for first-touch outcomes.

### Stage BTC-3: independent candidate discovery

Build BTC candidates from BTC data without importing GOLD thresholds or outcomes.

Freeze:

- feature formulas;
- candidate density;
- direction;
- target/stop contract;
- horizon;
- duplicate suppression;

before using final evaluation periods.

### Stage BTC-4: backtest/live parity

Verify:

- closed-bar decision parity;
- M1 first-touch parity;
- same-M1 SL priority;
- spread handling for LONG and SHORT;
- time exit;
- no-backfill initialization;
- restart recovery.

### Stage BTC-5: connect shared execution infrastructure

Only after BTC candidates and trade contracts are independently validated:

- assign BTC-specific magic base and comment prefix;
- create BTC-specific ledger/archive/output directories;
- create BTC notification profile;
- run Discord-only;
- run dry-run;
- perform a separately authorized smallest-volume real-order test.

## 7. GOLD and BTC coexistence requirements

They must have separate:

- system IDs;
- magic-number ranges;
- MT5 comment prefixes;
- candidate keys;
- state JSON;
- candidate registry;
- execution ledger;
- trade/deal archives;
- lock directories;
- stop files;
- output/log directories;
- Discord title/asset labels;
- volume and risk settings.

A shared webhook is possible, but notifications must make the asset unmistakable.

A global cross-asset position/risk cap is not currently implemented. If GOLD and BTC run together, each loop can know only its own local limit unless a new shared portfolio risk coordinator is added.

## 8. Important remaining design decisions for BTC

These are not decided yet:

- broker's exact BTC symbol;
- whether BTC runs in the same MT5 terminal/account;
- smallest safe BTC lot for that broker;
- fixed lot versus account-risk sizing;
- whether GOLD and BTC may hold positions simultaneously;
- BTC signal timeframes;
- BTC direction mix;
- BTC SL/TP and horizon contracts;
- BTC research period splits;
- separate or shared Discord channel.

## 9. New-chat starting prompt

Copy the following into the next chat:

```text
repo: knitanr-a11y/xauusd-signal-lab

Read first:
docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GML1_NOTIFICATION_AND_BTC_REUSE_20260702.md

Current main includes the live GOLD Discord/MT5 execution system from merged PR #69.
The user has run it for several days and reports one real signal, one real MT5 order, SL closure, and both entry and exit Discord notifications.

First task:
Improve the GOLD Discord signal and exit notification wording so it is easy to read in Japanese, without changing any candidate formula, direction, ATR stop, target R, horizon, order logic, duplicate prevention, archive logic or existing live state.

Important:
- The active formatter is live_execution_live_wr.py.
- Existing ledger columns do not include source_timeframe, higher_timeframe, features_json, ATR, target R or a human-readable reason.
- Separate presentation-only changes from schema-extension changes.
- Any ledger extension must migrate existing user-PC live_execution_ledger.csv additively. Never require deletion or reset.
- Preserve sent-notification markers and live win-rate history.
- Show proposed entry and exit notification examples before finalizing the wording.
- Add tests for old-ledger migration, Japanese status mapping, SL/TP/time/manual close display, missing fields, restart idempotency and Discord length.

Second task:
Begin BTC signal-system work using the reuse boundary in the handoff.
Reuse execution/log/archive infrastructure only after parameterization. Do not copy GOLD signal thresholds, candidate IDs, directions, contracts, 0.01 lot, magic numbers, outputs or validation results into BTC.
Start with BTC-0 broker/data-contract audit and create a separate BTC state/output namespace.
Keep the current GOLD live system operational and unchanged except for the notification layer.
```

## 10. Immediate priority order in the next chat

1. Preserve and inspect the existing GOLD live state contract.
2. Refactor notification formatting behind tests.
3. Present readable Japanese entry/exit examples.
4. Implement backward-compatible optional notification fields.
5. Verify no order/candidate behavior changed.
6. Start BTC-0 broker/data audit.
7. Design common execution interfaces without moving all GOLD code at once.
8. Create BTC research/data path separately.
