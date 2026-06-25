# Repository Agent Instructions

## GOLD_ML_V1

1. Use only the GOLD_ML_V1 namespace and its clean-rebuild contracts.
2. Do not use quarantined legacy GOLD logic or derived artifacts. Only explicitly authorized raw candle files are allowed.
3. Raw CSV `time` is bar-open time. Bar availability is open time plus timeframe duration. Never reinterpret this contract.
4. Preserve MT5 server timestamps. CSV latest rows are closed by contract.
5. Candidate logic is immutable. Changed logic requires a new ID.
6. The accumulated set contains nine entries: GML1-PROV-007, GML1-PROV-008, GML1-WATCH-022-B, GML1-PROV-010, GML1-PROV-015, GML1-PROV-020, GML1-WATCH-021-A, GML1-WATCH-021-B, GML1-WATCH-021-C.
7. GML1-WATCH-014-A, GML1-WATCH-022-A and GML1-WATCH-023-A remain research-only.
8. Batch023 registry parity and derivative-parent parity passed. Replay V1-V4 failures were replay-implementation failures, not candidate failures.
9. The frozen indicator contract uses Wilder ATR14 with SMA seed, EMA adjust=False, Bollinger ddof=0, RCI18 rank-difference formula, and dynamic spread point 0.01.
10. The current replay entrypoint is `scripts/gold_ml_v1/replay/replay_v5_entry.py`, launched by `scripts/gold_ml_v1/replay/run_batch023_all.bat`.
11. V5 fixes the M15 event contract: compute `active = state AND eligible` on the full M15 sequence, then detect false-to-true. Do not filter eligible rows before `shift()`.
12. V5 compares the three documented onset-order variants and accepts only exact PROV-007, PROV-008 and WATCH-022-B decision-set parity. Thresholds are never changed.
13. The H1-D1 lane uses the frozen Batch006 event-before-execution order with Wilder ATR and D1 RCI18.
14. Historical decisions and trade evaluation use only `gold_v3_2023_2026_*.csv` rows.
15. Exact-overlap-verified goldsharp rows strictly before the first historical timestamp may be used only as indicator warmup. Goldsharp rows after the historical maximum must not enter historical replay.
16. Weekend and broker-maintenance gaps are valid. Time exit uses the last available M1 close inside the wall-clock horizon.
17. Live closed-bar observation uses `goldsharp_*.csv`; historical rows never emit new live signals.
18. Use `scripts/gold_ml_v1/replay/run_batch023_all.bat` for the V5 rerun.
19. Do not continue exploration before V5 output and all nine parity reports are inspected.
20. Same-lineage candidates are not independent edges and must not be summed as a portfolio.
21. The 2026 sample is diagnostic only and cannot be used for retuning.
22. Remain audit-only. No live activation or automatic promotion.
23. Never claim completion until outputs are inspected.

Current status:

`GOLD_ML_V1_012_NINE_ACCUMULATED_CANDIDATES_BATCH023_REPLAY_V5_COMMITTED_LOCAL_RERUN_REQUIRED_AUDIT_ONLY`

Next phase:

`PULL_V5_RERUN_BATCH023_INSPECT_ALL_NINE_PARITY_REPORTS`
