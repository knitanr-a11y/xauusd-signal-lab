# GOLD_ML_V1 next chat prompt

Repository: `knitanr-a11y/xauusd-signal-lab`

Read these files first and in this order:

1. `docs/gold_ml_v1/NEXT_CHAT_START_HERE_20260626.md`
2. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_THREE_PASS_AUDIT_IMPLEMENTATION_AND_METRICS_20260626.md`
3. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_15_ACCUMULATED_9_WATCHES_20260626.md`
4. `docs/gold_ml_v1/GOLD_ML_V1_WATCH029_034_IMPLEMENTATION_CONTRACT_20260626.md`
5. `config/gold_ml_v1/implementation_status_and_metrics_20260626.json`
6. `config/gold_ml_v1/handoff_snapshot_20260626.json`
7. `config/gold_ml_v1/provisional_candidate_stack_20260624.json`

Current authority is stack `GOLD_ML_V1_PROVISIONAL_CANDIDATE_STACK_20260626_W`.

Current state:

- accumulated: 15
- research watches: 9
- retired: `GML1-WATCH-031-A`
- implementation level: 2 of 6
- executable implementations committed for WATCH-029 through WATCH-034: 0
- audit-only
- no live, order, notification, or final-signal changes

Important terminology:

- accumulated means accepted into the research stack; it does not mean implemented in executable code.
- implemented may be used only after an executable detector, exact-M1 integration and parity tests are committed.
- current WATCH-029 through WATCH-034 status is: audit prototype/backtest complete, config/metrics/contract committed, executable integration not complete.

Important rules:

- Use the stack file as the authority for candidate state.
- Use `implementation_status_and_metrics_20260626.json` as the authority for implementation completion and performance metrics.
- WATCH-029-A uses frozen source stack P with 13 proposal engines, not the current accumulated 15.
- WATCH-031-A stays retired and must not be implemented or reused.
- WATCH-033-A keeps component-specific TP5 and TP7.5 plus fixed priority.
- WATCH-034-A/B/C are mutually exclusive exit variants of one entry lineage; never combine their counts or submit them as three simultaneous trades.
- CSV time is MT5-server bar-open time and the latest CSV row is closed.
- Preserve exact M1 entry, dynamic bid/ask spread, protective-first same-M1 handling, and causal higher-timeframe joins.
- 2024-2026 has already been inspected. True prospective data starts after 2026-06-26.
- Do not change the frozen nine.
- Any logic, threshold, exit, or source-stack change requires a new candidate ID.
- Do not implement, promote, or enable runtime behavior without an explicit user request.

After reading, report only:

1. files read
2. stack ID
3. accumulated count
4. research-watch count
5. retired ID
6. implementation level and executable implementation count
7. confirmation that audit-only remains active

Then continue from the user's next instruction.
