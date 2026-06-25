# Repository Agent Instructions

## GOLD_ML_V1

1. Use only the GOLD_ML_V1 namespace and its clean-rebuild contracts.
2. Do not use quarantined legacy GOLD logic or derived artifacts. Only explicitly authorized raw candle files are allowed.
3. Raw CSV `time` is bar-open time. Bar availability is open time plus timeframe duration. Never reinterpret this contract.
4. Preserve MT5 server timestamps. CSV latest rows are closed by contract.
5. Candidate logic is immutable. Changed logic requires a new ID.
6. The accumulated set contains nine entries: GML1-PROV-007, GML1-PROV-008, GML1-WATCH-022-B, GML1-PROV-010, GML1-PROV-015, GML1-PROV-020, GML1-WATCH-021-A, GML1-WATCH-021-B, GML1-WATCH-021-C.
7. GML1-WATCH-014-A, GML1-WATCH-022-A and GML1-WATCH-023-A remain research-only.
8. Batch023 registry parity and derivative-parent parity passed.
9. Replay V1-V5 were reconstructed implementations and are not the source of truth. Their failures are implementation failures, not candidate failures.
10. The only accepted Batch023 historical evaluator is the verbatim `replay_nine_candidates.py` extracted at runtime from the verified ZIP with SHA256 `d1e9ab8cbeb7d73c8cf75f688bad39af0d64982901fbcd4474c1b230802b53b9`.
11. Launch the frozen evaluator through `scripts/gold_ml_v1/replay/run_frozen_batch023_from_zip.py` or `scripts/gold_ml_v1/replay/run_batch023_step3_v5.bat`.
12. Do not copy, rewrite, reinterpret or optimize the frozen evaluator logic before exact parity is established.
13. Historical replay raw input is the `gold_v3_2023_2026` directory only. Goldsharp files are not passed into frozen historical replay.
14. Live closed-bar observation uses `goldsharp_*.csv`; historical rows never emit new live signals.
15. Do not continue exploration before frozen Batch023 output and all nine parity reports are inspected.
16. Same-lineage candidates are not independent edges and must not be summed as a portfolio.
17. The 2026 sample is diagnostic only and cannot be used for retuning.
18. Remain audit-only. No live activation or automatic promotion.
19. Never claim completion until outputs are inspected.

Current status:

`GOLD_ML_V1_013_BATCH023_FROZEN_ORIGINAL_EVALUATOR_LAUNCHER_COMMITTED_LOCAL_RERUN_REQUIRED_AUDIT_ONLY`

Next phase:

`PULL_FROZEN_LAUNCHER_RERUN_STEP3_INSPECT_ALL_NINE_PARITY_REPORTS`
