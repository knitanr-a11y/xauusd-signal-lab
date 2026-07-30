# NEXT CHAT HANDOFF — BTC candidate research

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T12:42:00+09:00`
- status: `BTC_REDESIGN_BCR03_CONTENT_CLOCK_FEATURE_PARITY_COMPLETE_ORIGINAL_PATH_PENDING`
- next action: obtain the exact original absolute path of the submitted BTC M15 CSV

## 1. Startup hard gate

Use only branch:

`feature/btc-fresh-forward-research`

Do not use `main`, default branch, similar files or old handoffs as current state.

Read `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md` first and follow its exact read order.

## 2. Project purpose

Build two BTC candidate research tracks:

- Track A: Mochipoyo-source-anchored BTC candidate research using genuine M7C/Collector source alerts.
- Track B: independent-vector BTC candidate research based on different market mechanisms.

The system objective includes future profitability, stability, loss control, complementary behavior, shadow parity, drift monitoring and fail-closed retirement. A visually attractive isolated backtest is not sufficient.

## 3. Runtime protection

Do not stop, restart, initialize or modify:

- Collector
- M7C
- M8C
- M9 series
- M10 series

Do not write BTC research outputs into GOLD/MOCHIPOYO runtime folders.

Discord, MT5 order, live-ready, lot design and automatic promotion remain forbidden.

## 4. Preserved completed work

### D1 M7C and Collector provenance

- M7C package SHA256: `870ea28c530f1db603afb190a0daa84963b6c7c3d4142ca0859dce1ddb655295`
- Collector package SHA256: `b65ddd0b7c240d5acd26c271b228142929574d82ad5e96eadec1e1f37d62b3fe`
- M7C supported source events at D1: 90
- M7C supported BTCUSD: 51
- Collector cursor and retry behavior accepted
- no performance interpretation performed

### BCR01 outcome-blind source snapshot

Valid package:

- file: `99_UPLOAD_PACKAGE(102).zip`
- SHA256: `bc562948ee8baefba32d0e291a54341243da4684bdbf43d652676d5fcdab5611`
- snapshot: `BCR01_20260730T030649Z_RAWMAX194`
- raw IDs: 1–194 contiguous
- cursor: 194
- payload/identity mismatches: 0
- outcome tables read: false

The earlier BCR01 v1.0.0 error package is audit history only.

### BCR02 canonical source event ledger

- package SHA256: `5251428a456b7ee0a659d9ccd4b7ea2d4afde5e7e426c0b5da1ca60c5d0576b2`
- prospective research IDs: 64–194
- research rows: 131
- BTCUSD rows: 76
- BTC M7C-v1 supported primary/valid-exit events: 53
- M7C state parity IDs 64–188: 125/125 exact
- outcomes opened: false

### BCR02A fidelity decomposition

BTC primary source events:

- total: 25
- correct RCI turn: 25/25
- correct EMA stack: 22/25
- M7C missed primary: 11
- missed primary with prior state divergence: 9
- missed primary with RCI turn mismatch: 0

The primary signature is not random. Exit delay/miss can cause state divergence that cascades into later rejected primary events. Profitability is not established.

## 5. BCR03 submitted M15 content

User submitted:

`btcusdsharp_m15(3).csv`

The upload suffix `(3)` is not authoritative local provenance.

Content SHA256:

`b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`

Content inventory:

- bytes: 2,110,267
- rows: 30,661
- schema: `time,open,high,low,close,tick_volume,spread,real_volume`
- earliest server open: `2025-09-13 08:00:00`
- latest server open: `2026-07-30 06:15:00`
- duplicate timestamps: 0
- timestamp parse errors: 0
- monotonic increasing: true
- explicit gap transitions: 47
- implied missing M15 bars: 53

Do not interpolate gaps.

## 6. BCR03 event and clock mapping

Frozen mapping for this inspected interval:

`MT5 server open = source bar_time_utc + 3 hours`

For all 76 BCR02 BTC source events:

- current server-open row found: 76/76
- immediately previous closed M15 row found: 76/76
- event at gap boundary: 0
- previous closed event bar at gap boundary: 0

The +3 offset was the clear descriptive price-fit winner among tested integer offsets:

- +3 median absolute source/current-open difference: 3.88
- +2 median absolute difference: 105.52

Do not generalize this offset across uninspected DST periods.

## 7. Exact M7C feature parity

The submitted CSV was used to recompute BTC M7C values at all accepted BTC proxy decision rows.

Rows tested: 890.

Exact parity within floating-point precision:

- RCI9: 890/890
- EMA20-minus-EMA30 bps: 890/890
- EMA30-minus-EMA40 bps: 890/890

This is strong evidence that the submitted CSV contains the exact BTC M15 close sequence used by M7C for all inspected decisions.

## 8. Causal feature boundary

Allowed:

- fully closed M15 history before decision
- current M15 open only
- deterministic indicators from fully closed M15 bars
- explicit gap flags without filling gaps

Forbidden:

- current M15 high/low/close
- later M15 bars
- interpolated bars
- future HTF close
- outcome, MFE, MAE, TP/SL result or later profitability

Higher-timeframe features remain pending a separate as-of close-availability contract.

## 9. Current blocker

Only one provenance field is missing:

`the exact original absolute local path from which the submitted CSV was copied`

The new chat must not guess the path from the upload name, modification time, MetaQuotes convention or old files.

Ask the user to paste the full Windows path exactly. No additional upload is required unless the path identifies a different file or multiple plausible files.

## 10. Current authorization

Authorized now:

- receive and record the exact original absolute path
- verify that the stated path corresponds to this submitted content/source role
- close BCR03 provenance if consistent
- design the next outcome-blind research contract after BCR03 closes

Not authorized yet:

- candidate formula freeze
- outcome performance interpretation
- WR/PF/DD/MFE/MAE
- TP/SL optimization
- FF06
- shadow runtime
- live action

## 11. Exact current references

Read:

- `docs/btc_ml_v1/BTC_BCR03_M15_CONTENT_CLOCK_AND_M7C_FEATURE_PARITY_AUDIT_20260730.md`
- `configs/btc_ml_v1/btc_bcr03_m15_content_clock_feature_parity_result_20260730.json`
- `docs/btc_ml_v1/BTC_BCR03_BTC_SOURCE_TO_MT5_CANDLE_MAPPING_CONTRACT_20260730.md`
- `docs/btc_ml_v1/BTC_BCR02_CANONICAL_SOURCE_EVENT_LEDGER_20260730.md`
- `docs/btc_ml_v1/BTC_BCR02A_M7C_FIDELITY_DECOMPOSITION_OUTCOME_BLIND_20260730.md`

Do not restart FF05 recovery work. BTC7R remains quarantined. FF01–FF04 causal/time semantics remain preserved as audit evidence only.
