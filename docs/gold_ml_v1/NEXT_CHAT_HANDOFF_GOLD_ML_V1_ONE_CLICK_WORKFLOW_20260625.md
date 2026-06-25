# GOLD_ML_V1 — One-Click Workflow / Complete Next-Chat Handoff

Date: 2026-06-25  
Repository: `knitanr-a11y/xauusd-signal-lab`  
Mode: **AUDIT ONLY**

## 1. Start here — mandatory read order

Every new chat must read these files before proposing or changing anything:

1. `AGENTS.md`
2. `config/gold_ml_v1/current_state_snapshot_20260624.json`
3. `config/gold_ml_v1/next_local_action.json`
4. `config/gold_ml_v1/batch023_uploaded_raw_forensic_audit_20260625.json`
5. `config/gold_ml_v1/batch023_warmup_bridge_pass_20260625.json`
6. `config/gold_ml_v1/batch023_local_warmup_bridge_implementation_20260625.json`
7. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_BATCH023_WARMUP_BRIDGE_PASS_20260625.md`
8. This file

Do not ask the user to repeat any fact already recorded in these files.

## 2. Current authoritative status

`GOLD_ML_V1_016_BATCH023_WARMUP_BRIDGE_9_OF_9_CORE_PARITY_PASS_AUDIT_ONLY`

The user ran the validated local implementation successfully.

Uploaded proof files:

- `LATEST_RUN_SUMMARY.txt`
- `warmup_bridge_summary.json`
- nine `*_warmup_bridge_core_registry.csv`
- nine `*_warmup_bridge_exact_schema_registry.csv`

The uploaded run says:

- status: PASS
- exit code: 0
- Batch023 ZIP SHA256 matches
- all six raw CSV SHA256 values match
- all nine candidates pass
- missing/extra: 0
- entry mismatch: 0
- exit mismatch: 0
- R mismatch: 0
- direction mismatch: 0

## 3. Verified uploaded registry inventory

| Candidate | Total | RAW_RECONSTRUCTED | WARMUP_BRIDGE_EXACT | Duplicate decisions | Decision range |
|---|---:|---:|---:|---:|---|
| GML1-PROV-007 | 154 | 153 | 1 | 0 | 2023-01-10 04:00 — 2026-06-17 01:15 |
| GML1-PROV-008 | 169 | 168 | 1 | 0 | 2023-01-10 04:00 — 2026-06-17 01:15 |
| GML1-WATCH-022-B | 135 | 134 | 1 | 0 | 2023-01-10 04:00 — 2026-06-17 01:15 |
| GML1-PROV-010 | 254 | 242 | 12 | 0 | 2023-01-06 21:00 — 2026-04-17 16:00 |
| GML1-PROV-015 | 225 | 213 | 12 | 0 | 2023-01-06 21:00 — 2026-04-17 16:00 |
| GML1-PROV-020 | 204 | 193 | 11 | 0 | 2023-01-06 21:00 — 2026-04-17 16:00 |
| GML1-WATCH-021-A | 210 | 200 | 10 | 0 | 2023-01-09 04:00 — 2026-04-17 16:00 |
| GML1-WATCH-021-B | 207 | 197 | 10 | 0 | 2023-01-06 21:00 — 2026-04-17 16:00 |
| GML1-WATCH-021-C | 196 | 187 | 9 | 0 | 2023-01-09 04:00 — 2026-04-17 16:00 |

## 4. Fixed contracts — do not reinterpret

### General

- Raw CSV `time` is the bar-open time.
- Time basis is MT5 server naive time. Do not convert to JST for candidate decisions.
- CSV latest rows are closed by contract.
- Candidate rules and thresholds are immutable. A changed rule requires a new candidate ID.
- Same-lineage candidates are not independent portfolio edges. Do not sum their metrics.
- The 2026 period is diagnostic only and must never be used for retuning.

### M15–H4 lineage

- H4 RCI18: rank-difference RCI on H4 close.
- H4 state spread/ATR: spread price divided by simple rolling TR14.
- H4 EMA40 slope6/ATR: EMA40 adjust=False slope divided by Wilder ATR14.
- M15 trade ATR: simple rolling TR14.
- M15 Bollinger: population standard deviation (`ddof=0`) divided by simple ATR14.
- BB60 trailing-100 percentile: fraction of trailing values less than or equal to the current value.
- Event onset: false-to-true of `state AND exact-M1-entry eligibility` on the full M15 sequence.
- Same-M1 TP/SL collision: SL first.
- Hit and time-exit timestamp storage: M1 bar-close time.

### H1–D1 lineage

- H1 BB60: population standard deviation (`ddof=0`).
- D1 RCI18: rank-difference RCI on D1 close.
- H1 trade and spread ATR: Wilder ATR14.
- D1 tick-volume ratio50: rolling median50, not rolling mean.
- D1 delta3/ATR: three-bar close delta divided by Wilder ATR14.
- Same-M1 TP/SL collision: SL first.
- Hit and time-exit timestamp storage: M1 bar-open time.
- If the nominal horizon minute is unavailable, use the last available M1 close price inside the wall-clock horizon.

## 5. Warmup bridge policy

Every output row is marked as:

- `RAW_RECONSTRUCTED`
- `WARMUP_BRIDGE_EXACT`

`WARMUP_BRIDGE_EXACT` rows exist only because the supplied raw snapshot begins in January 2023 and lacks pre-2023 indicator state.

Mandatory restrictions:

- This is not raw-only parity.
- Bridge rows are historical audit rows only.
- Bridge rows must never generate live signals.
- Bridge rows must be reported separately in stress tests.
- Full raw-only parity requires pre-2023 candles or serialized indicator state.

## 6. One-click operating contract

The user must not be given a new long command for every phase.

The only user-facing entrypoint from now on is:

`RUN_GOLD_ML_V1_NEXT.bat`

The user workflow must always be:

1. Assistant completes and commits the next phase implementation to GitHub.
2. Assistant updates `config/gold_ml_v1/next_local_action.json` to point at the new phase BAT.
3. Assistant verifies syntax/tests as far as available.
4. Assistant tells the user only: **Pull, then double-click `RUN_GOLD_ML_V1_NEXT.bat`.**
5. User pastes or uploads the resulting summary files.

Do not ask the user to type Python commands, PowerShell commands, or multi-argument BAT commands unless the one-click dispatcher itself is broken and the reason is proven.

## 7. Stable dispatcher design

Stable files:

- `RUN_GOLD_ML_V1_NEXT.bat`
- `scripts/gold_ml_v1/run_next_local.py`
- `config/gold_ml_v1/next_local_action.json`

`RUN_GOLD_ML_V1_NEXT.bat` never changes for ordinary phases. Future chats update only the action config and add a phase-specific BAT/Python implementation.

The dispatcher:

- uses an existing project virtual environment when available;
- reads the action config;
- detects the MQL5 `Files` ancestor when the repository is stored below it;
- supports optional private overrides from `config/gold_ml_v1/local_runtime_paths.local.json`;
- writes `outputs/gold_ml_v1/next_action/LATEST_NEXT_ACTION.txt`;
- returns the phase runner's exit code.

Private path overrides are ignored by Git and must never be committed.

## 8. Current dispatcher state

`config/gold_ml_v1/next_local_action.json` is currently `status_only` because Batch023 warmup bridge verification is already complete.

It must not rerun V1–V5 or the old frozen evaluator.

The next chat must first implement the next phase, then change the config to `mode: bat`.

## 9. Next phase

`COST_STRESS_RAW_RECONSTRUCTED_ONLY_REPORT_BRIDGE_SEPARATELY_THEN_FRESH_PROSPECTIVE`

The next implementation must:

1. Read the nine locally generated warmup-bridge registries.
2. Use `RAW_RECONSTRUCTED` rows as the primary cost-stress population.
3. Report `WARMUP_BRIDGE_EXACT` rows separately.
4. Run at minimum:
   - spread ×1.5
   - spread ×2.0
   - fixed slippage stress
5. Preserve candidate IDs and lineage.
6. Produce machine-readable CSV/JSON and a plain-text latest summary.
7. Fail closed when required input or provenance does not match.
8. Remain audit-only.

The exact fixed-slippage grid must be explicitly recorded in the next phase config before execution. Do not silently invent or change it after seeing results.

## 10. Forbidden actions

- Do not rerun or revive replay V1, V2, V3, V4, or V5.
- Do not call the ZIP-bundled replay script the original generator.
- Do not silently fill bridge rows into live or prospective data.
- Do not retune using 2026.
- Do not activate MT5 orders, Discord, AI API, live hooks, or final signals.
- Do not register/promote candidates before cost stress and fresh prospective confirmation.
- Do not ask the user to repeat paths or decisions already recorded.

## 11. Failure handling

Every phase BAT must:

- create its output directory before writing;
- back up or safely replace previous outputs;
- print a clear PASS/FAIL line;
- return `0` only for PASS;
- return a non-zero code for validation failure;
- write a latest summary and an error trace;
- never continue automatically into live activation.

The user should upload these files after a run:

- `outputs/gold_ml_v1/next_action/LATEST_NEXT_ACTION.txt`
- the phase-specific `LATEST_RUN_SUMMARY.txt`
- phase-specific summary JSON/CSV

## 12. If the chat is near its length limit

Before the conversation ends, the assistant must update all of:

- `AGENTS.md`
- `config/gold_ml_v1/current_state_snapshot_20260624.json`
- `config/gold_ml_v1/next_local_action.json`
- a dated `NEXT_CHAT_HANDOFF_*.md`

The response must identify the exact GitHub commit SHAs. Never leave continuation dependent only on chat history.
