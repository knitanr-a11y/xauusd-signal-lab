# GOLD_ML_V1 next chat prompt

Repository: `knitanr-a11y/xauusd-signal-lab`

Read these files first:

1. `docs/gold_ml_v1/NEXT_CHAT_START_HERE_20260626.md`
2. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_15_ACCUMULATED_9_WATCHES_20260626.md`
3. `docs/gold_ml_v1/GOLD_ML_V1_WATCH029_034_IMPLEMENTATION_CONTRACT_20260626.md`
4. `config/gold_ml_v1/handoff_snapshot_20260626.json`
5. `config/gold_ml_v1/provisional_candidate_stack_20260624.json`

Current authority is stack `GOLD_ML_V1_PROVISIONAL_CANDIDATE_STACK_20260626_W`.

Current state:

- accumulated: 15
- research watches: 9
- retired: `GML1-WATCH-031-A`
- audit-only
- no live, order, notification, or final-signal changes

Important rules:

- Use the stack file as the authority for candidate state.
- WATCH-029-A uses frozen source stack P with 13 proposal engines, not the current accumulated 15.
- WATCH-031-A stays retired because it contained targets below the required minimum target of 5 XAUUSD price dollars.
- WATCH-033-A keeps component-specific TP5 and TP7.5 plus fixed priority.
- WATCH-034-A/B/C are mutually exclusive exit variants of one entry lineage.
- CSV time is MT5-server bar-open time and the latest CSV row is closed.
- Preserve exact M1 entry, dynamic bid/ask spread, protective-first same-M1 handling, and causal higher-timeframe joins.
- 2024-2026 has already been inspected. True prospective data starts after 2026-06-26.
- Do not change the frozen nine.
- Any logic, threshold, exit, or source-stack change requires a new candidate ID.
- Do not implement, promote, or enable runtime behavior without an explicit user request.

After reading, report only the files read, stack ID, accumulated count, research-watch count, retired ID, and confirmation that audit-only remains active. Then continue from the user's next instruction.
