# NEXT CHAT HANDOFF — GOLD V3 Stage215 done, Stage216 result next

Date: 2026-06-16
Repo: `knitanr-a11y/xauusd-signal-lab`
Status: GOLD V3 audit-only / no-send / no-order / no-live-hook

## Read this first in the next chat

Read this handoff only, then read the user's attached Stage216 `paste_me.txt` result.

Do not read broad legacy docs or old signal-candidate docs unless the user explicitly asks.

## Absolute don't-read / don't-use list

- GOLD V2
- old GOLD
- DISC8
- Stage41 feature-only snapshot as any trading source
- quarantined or legacy signal candidate docs
- old candidate-pool exploration docs unless explicitly requested for audit traceback

## Hard guardrails

- GOLD V3 is audit-only.
- CSV latest row is contractually closed. Do not treat it as open/as-of.
- Do not remove candidate pool silently.
- Do not bypass F002 exclusion.
- Do not enable Discord, MT5 order, AI API, payload, live hook, final live, or autotrade.
- NO_SIGNAL must not notify Discord.
- Entry/candidate/gate logic must use only live-entry-available data.
- Future TP/SL/exit/horizon outcomes are audit/backtest scoring only, never entry inputs.
- Health/rolling/history gates can only use resolved results with `exit_dt <= current entry_dt`.
- Use MT5/CSV timestamp basis. Do not convert to JST for detector logic.

## Current canonical portfolios

### PRIMARY ABC CAP portfolio, priority A > C > B

```text
A_PRECISION_BASE:
  d1_dist_close_atr28<=-0.438769 & h4_body_atr14>=0.883347
  LONG TP40 SL20 horizon192

C_BALANCED_CAP60:
  d1_dist_close_atr28<=-0.263261 & h4_body_atr14>=0.530008 & h1_atr14<=60
  LONG TP30 SL30 horizon192

B_HIGH_FREQUENCY_CAP40:
  d1_dist_close_atr28<=-0.394892 & h1_atr14<=40
  LONG TP50 SL30 horizon192
```

### SECONDARY_AUDIT_CANDIDATE

Use the current OHLC recomputed secondary strategy only:

```text
SCALP_ONE_POSITION_FILTERED_V1_OHLC_RECOMPUTED
```

Do not call it a watchlist. It is a secondary audit candidate / scalp secondary candidate / 補助戦略候補.

## Completed recent stages

### Stage199

Frozen current secondary candidate from OHLC recomputed route.

Decision:

```text
STAGE199_SCALP_FILTERED_V1_OHLC_RECOMPUTED_FREEZE_READY_AUDIT_ONLY
```

Key point:

- use OHLC recomputed route, not older Stage191 artifact as source of truth
- cost5 is a worse-execution stress proxy, not spread-only

### Stage200–202

No-send preview packet and clean retention design.

Key policy:

- latest_state overwrite
- signal_events / trade_signal ledger append only on signal
- NO_SIGNAL full rows are not appended
- NO_SIGNAL counter/health rollup only

### Stage203–205

Retention writer dry-run and actual execution ledger/import contracts.

Key policy:

- final live performance must eventually use actual execution ledger
- theoretical result ledger remains for strategy-vs-execution separation
- no actual order/import enabled yet

### Stage206

Theoretical result resolver dry-run passed.

Known replay signal:

```text
signal_id: 20260615_163000_SECONDARY_AUDIT_CANDIDATE_SCALP_024_tp15_sl5_hz64_SHORT
entry_dt: 2026-06-15 16:30
candidate: SCALP_024_tp15_sl5_hz64_SHORT
SHORT entry 4363.24 TP15 SL5 horizon64
M5 theoretical result: SL at 2026-06-15 16:40
pnl_raw -5.0 / cost3 -8.0 / cost5 -10.0
```

### Stage207

Actual execution import contract ready.

Preferred match key:

```text
signal_id
```

Fallback:

```text
symbol + direction + time window + entry price tolerance
```

### Stage208

Signal ID embedding contract ready.

Known signal short id:

```text
full signal_id: 20260615_163000_SECONDARY_AUDIT_CANDIDATE_SCALP_024_tp15_sl5_hz64_SHORT
short_signal_id: G3SD01960980A23107A65AE
```

### Stage209–210

No-send live-cycle packet and append writer dry-run passed for NO_SIGNAL cycle.

### Stage211

Integrated no-send cycle runner from OHLC passed.

Decision:

```text
STAGE211_INTEGRATED_NO_SEND_CYCLE_RUNNER_READY_AUDIT_ONLY
```

Latest at the time:

```text
latest_closed_m15_dt: 2026-06-16 16:45:00
latest_final_route: NO_SIGNAL
trade_signal_append_preview_rows: 0
notification_append_preview_rows: 0
no_signal_counter_preview_rows: 1
```

### Stage212

Integrated route parity passed; feature drift is WARN.

Decision:

```text
STAGE212_ROUTE_PARITY_PASS_FEATURE_DRIFT_WARN_AUDIT_ONLY
```

Key result:

```text
tail_overlap_rows: 90
tail_overlap_route_parity_pass: True
feature_drift_warn_rows: 16
feature_drift_blocks_live: False
```

Feature drift details:

```text
h1_atr14 drift rows: 2
h4_body_atr14 drift rows: 14
all affected rows stayed NO_SIGNAL -> NO_SIGNAL
```

### Stage213

Readiness summary passed, but live release remains blocked.

Decision:

```text
STAGE213_READINESS_GATE_SUMMARY_READY_LIVE_RELEASE_BLOCKED_AUDIT_ONLY
```

Capabilities ready:

```text
8 / 8
```

Live release status:

```text
NO_SEND_INTEGRATED_DRY_RUN_READY_LIVE_RELEASE_BLOCKED
```

Remaining hard blocks:

```text
HB001 live retention writer not enabled
HB002 Discord send not enabled and not approved
HB003 MT5 order execution not enabled and not approved
HB005 latest SIGNAL cycle after Stage211 not observed in live integrated runner
HB006 duplicate signal_id handling not audited yet
```

### Stage214

Repeat-safe / idempotent writer dry-run passed.

Decision:

```text
STAGE214_IDEMPOTENT_WRITER_DUPLICATE_SIGNAL_ID_READY_AUDIT_ONLY
```

Rules:

```text
trade_signal_ledger.csv: duplicate signal_id -> SKIP_DUPLICATE_SIGNAL_ID
notification_events_rolling_30d.csv: duplicate signal_id/short_signal_id -> SKIP_DUPLICATE_NOTIFICATION_EVENT
no_signal_counters_daily_hourly.csv: duplicate latest_closed_m15_dt + final_route -> SKIP_DUPLICATE_COUNTER_INCREMENT
latest_state.json -> OVERWRITE
debug_tail_snapshot.csv -> REPLACE_ROLLING_SNAPSHOT
```

### Stage215

SIGNAL case append preview replay passed.

Decision:

```text
STAGE215_SIGNAL_CASE_APPEND_PREVIEW_REPLAY_READY_AUDIT_ONLY
```

Replay signal:

```text
signal_id: 20260615_163000_SECONDARY_AUDIT_CANDIDATE_SCALP_024_tp15_sl5_hz64_SHORT
short_signal_id: G3SD01960980A23107A65AE
route: SECONDARY_AUDIT_CANDIDATE
candidate_id: SCALP_024_tp15_sl5_hz64_SHORT
direction: SHORT
entry_price: 4363.24
TP15 SL5 horizon64
```

Append preview:

```text
trade_signal_append_preview_rows: 1
notification_append_preview_rows: 1
no_signal_counter_preview_rows: 0
send_action: NO_SEND_AUDIT_ONLY
```

## Stage216 created but result not yet reviewed in this chat

Stage216 files were created.

Commits:

```text
Stage216 script: 30c008a61a76588e00bdf18ecb795e17d72edc43
Stage216 BAT: c340f454508e95a6eef364ba62de8c87e65ec43e
Stage216 spec: 9615a8ded53459252c15bfce2d5c0d62b427cfef
```

Run BAT:

```text
Scripts\gold_v3_runtime\bat\run_gold_v3_216_feature_drift_audit.bat
```

The user will attach Stage216 `paste_me.txt` in the next chat.

Expected output file:

```text
MQL5\Files\FX_OUTPUTS\gold_v3\216\paste_me.txt
```

## What to do first in next chat

1. Read this handoff.
2. Read the user's attached Stage216 result.
3. Determine whether Stage216 passed or blocked.
4. If Stage216 passes, proceed to Stage217.
5. If Stage216 blocks, fix only Stage216 logic; do not touch live send/order paths.

## Likely next stages after Stage216

### Stage217 recommended

```text
GOLD_V3_217_LIVE_RETENTION_WRITER_DRY_RUN_TO_STAGING_AUDIT_ONLY
```

Purpose:

- write previews to staging files only
- do not mutate production/live retention files
- validate real file append/overwrite mechanics safely
- keep Discord/MT5/order/import/payload/live hook/autotrade OFF

### Stage218 after Stage217

```text
GOLD_V3_218_STAGING_RETENTION_REPLAY_MULTI_CYCLE_AUDIT_ONLY
```

Purpose:

- replay multiple cycles into staging
- verify idempotency over repeated runs
- verify NO_SIGNAL counters, SIGNAL append rows, and rolling debug snapshot over more than one cycle

### Stage219 later

```text
GOLD_V3_219_NOTIFICATION_PAYLOAD_TEXT_PREVIEW_AUDIT_ONLY
```

Purpose:

- preview Discord message text only
- no send
- no webhook
- no payload activation

## Start prompt for next chat

Use the separate `NEXT_CHAT_START_PROMPT_GOLD_V3_215_DONE_216_RESULT_NEXT_AUDIT_ONLY_20260616.md` prompt.
