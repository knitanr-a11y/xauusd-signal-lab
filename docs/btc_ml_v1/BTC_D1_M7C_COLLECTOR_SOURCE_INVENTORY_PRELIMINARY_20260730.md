# BTC D1 M7C / Collector source inventory — preliminary contract-only pass

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30`
- status: `PRELIMINARY_CONTRACT_ONLY_LOCAL_ARTIFACTS_NOT_YET_INSPECTED`

## 1. Purpose

This D1 pass inventories only authoritative GitHub contracts. It does not inspect the user's current local M7C/collector evidence files, does not read outcomes, and does not propose BTC candidate formulas.

## 2. Authoritative contract evidence read

1. `docs/mochipoyo_alert_research/SCOPE_CLARIFICATION_M10_GOLD_ONLY_M7C_DUAL_SOURCE_BACKGROUND_20260727.md`
   - blob SHA: `5834455652abef3cdba891945188426c542a199c`
   - proves M10 is GOLD-only while M7C remains a frozen dual-symbol BTCUSD/XAUUSD background source-fidelity track.

2. `docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M7C_24_SUPPORTED_CONTINUE_TO_FORMAL_GATE_V2_20260722.md`
   - blob SHA: `24cd37ab4e3458cd710c4b2d96676ee25321964e`
   - defines M7C prospective start, formula, state transitions, timing contract, matching contract, local evidence filenames and prohibitions.

3. `config/mochipoyo_alert_research/objective_coverage_plus_value_add_20260722.json`
   - blob SHA: `727c47a2b567899f39c0f6b51270938e3f30bf81`
   - freezes coverage-first plus value-add objective and required separation of source matched, missed source and extra candidates.

4. `config/mochipoyo_alert_research/current_state_20260727.json`
   - blob SHA: `5bf0bc5442465c020e2535319f49f5902d36ad09`
   - requires collector, M7C, M8C, M9V, M9Y, M10B, M10E, M10P, M10P2 and M10W monitors to remain unchanged.

## 3. Confirmed source role

- M7C is not a GOLD-only system. It is a frozen prospective source-fidelity track for both BTCUSD and XAUUSD.
- BTCUSD observations are directly relevant to the new BTC source-anchored research.
- XAUUSD observations may be used only as secondary structural comparison unless a later contract justifies pooling.
- Current GOLD-only M10 candidate research must not be silently broadened to BTC.
- The BTC project must not alter or restart any running MOCHIPOYO monitor.

## 4. Confirmed M7C prospective and causal contract

- frozen prospective start: `2026-07-20T14:54:15Z`
- timeframe: M15
- decision at new M15 bar start
- previous fully closed M15 features only
- current M15 open only
- current high/low/close forbidden
- future bars forbidden
- historical replay forbidden for prospective scoring
- cross-timeframe candidate extraction forbidden in the frozen M7C formula
- one-to-one source matching
- exact and within-one-M15 matching rules frozen
- grace period frozen

Frozen transitions recorded by the contract:

- PRIMARY_LONG: `IDLE AND rci9_turn_up AND BULLISH_STACK`
- PRIMARY_SHORT: `IDLE AND rci9_turn_down AND BEARISH_STACK`
- LONG_EXIT: `ACTIVE_LONG AND rci9 >= 78.333333333333`
- SHORT_EXIT: `ACTIVE_SHORT AND rci9 <= -75`
- REENTRY: `NOT_MODELED_OR_SCORED`

These formulas are evidence about the current M7C proxy. They are not yet accepted as the complete Mochipoyo source formula or as a profitable BTC trade rule.

## 5. Confirmed evidence classes

The D1 event inventory must preserve at least:

- `SOURCE_MATCHED`
- `MISSED_SOURCE`
- `EXTRA_CANDIDATE`
- `EXTRA_ACCEPTED`
- `EXTRA_REJECTED`
- unsupported REENTRY separated from formal recall

Entry and exit transitions are signal events, not automatically one trade per row. Counts from the 2026-07-22 handoff are historical snapshots only and must not be treated as the user's current counts.

## 6. Current local evidence allowlist from the frozen handoff

Expected directory:

`%LOCALAPPDATA%/xauusd_signal_lab/mochipoyo_alert_research/logs/m7c`

Primary seven artifacts:

1. `latest_m7c_prospective_shadow.json`
2. `latest_m7c_shadow_loop_status.json`
3. `latest_m7c_source_event_comparisons.csv`
4. `latest_m7c_extra_proxy_signals.csv`
5. `latest_m7c_proxy_signals.csv`
6. `latest_m7c_proxy_decisions.csv`
7. `m7c_shadow_forever.log`

Collector artifacts are added only when source provenance, cursor, missing event, late event or collector failure cannot be resolved from the primary seven:

- `collector_forever.log`
- `latest_loop_status.json`
- `latest_collection_result.json`

## 7. What is not yet known without current local artifacts

1. Current row counts, current symbol counts and transition counts.
2. Exact columns, data types and schema versions of each CSV/JSON.
3. Genuine source event timestamp field and collection timestamp field.
4. Whether source timestamps are UTC, broker-server time, application time or mixed.
5. BTCUSD source symbol naming and whether it matches the BTC research candle source.
6. Duplicate, revision, late-event and cursor semantics in actual current data.
7. Exact mapping between source events, M7C decisions, proxy signals and proxy decisions.
8. Whether any current artifact contains outcome, MFE, MAE, win/loss, PF or other exposed performance fields.
9. Which events have already had outcomes inspected in prior chats or reports.
10. Whether local artifacts changed during read/copy.

Unknown items must not be guessed.

## 8. Required stable-read procedure for the local artifacts

- inspect the seven primary files as one set, not piecemeal;
- record absolute path, SHA256, bytes and mtime before reading;
- parse schemas and non-outcome counts only;
- record SHA256 again after reading;
- invalidate the inventory if any file changes during the read;
- do not write into the M7C directory;
- do not stop or restart M7C/collector;
- do not open outcome fields during D1;
- do not create candidate formulas during D1.

## 9. D1 preliminary conclusion

The source-anchored BTC research is justified because M7C formally includes BTCUSD and preserves genuine-source comparisons. However, a candidate grammar cannot be responsibly designed from the GitHub contracts alone. The current local seven-file evidence set is required to establish schema, timestamp, state and event-provenance facts first.

No BAT, candidate formula, outcome analysis, FF06 stage or shadow runtime is authorized by this preliminary inventory.
