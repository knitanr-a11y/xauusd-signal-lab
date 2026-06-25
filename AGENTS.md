# Repository Agent Instructions

## GOLD_ML_V1

1. Use only the GOLD_ML_V1 namespace and its clean-rebuild contracts.
2. Do not use quarantined legacy GOLD logic or derived artifacts. Only explicitly authorized raw candle files are allowed.
3. Raw CSV `time` is bar-open time. Bar availability is open time plus timeframe duration. Never reinterpret this contract.
4. Preserve MT5 server timestamps. CSV latest rows are closed by contract.
5. Candidate logic is immutable. Changed logic requires a new ID.
6. The accumulated set contains nine audit-only entries: GML1-PROV-007, GML1-PROV-008, GML1-WATCH-022-B, GML1-PROV-010, GML1-PROV-015, GML1-PROV-020, GML1-WATCH-021-A, GML1-WATCH-021-B, GML1-WATCH-021-C.
7. GML1-WATCH-014-A, GML1-WATCH-022-A and GML1-WATCH-023-A remain research-only.
8. Exact CSV SHA, row-count and derivative-filter audits passed for the supplied registry bodies. This does not establish raw-candle replay provenance.
9. Read `config/gold_ml_v1/batch023_provenance_failure_20260625.json` before any Batch023 work.
10. Replay V1-V5 and the ZIP-bundled `replay_nine_candidates.py` all fail to reproduce the bundled exact registries from the authorized `gold_v3_2023_2026` CSVs. The ZIP script is not the original generator.
11. Do not run or describe `run_batch023_step3_v5.bat`, `run_frozen_batch023_from_zip.py`, or reconstructed replay scripts as exact/original replay tools.
12. The actual original registry-generation script/notebook/environment and exact raw snapshot hashes are not preserved in the repository or Batch023 ZIP.
13. Raw parity is blocked until the original generator and raw snapshot are recovered, or a separately versioned reconstruction is created and clearly labeled non-original.
14. Historical raw input remains `gold_v3_2023_2026_*.csv`; live closed-bar observation remains `goldsharp_*.csv`. Never mix historical rows into new live decisions.
15. Same-lineage candidates are not independent edges and must not be summed as a portfolio.
16. The 2026 sample is diagnostic only and cannot be used for retuning.
17. Remain audit-only. No live activation, registration, automatic promotion, MT5 order, or Discord signal.
18. Never claim completion until provenance and raw parity are independently verified.

Current status:

`GOLD_ML_V1_014_BATCH023_ORIGINAL_GENERATOR_NOT_PRESERVED_RAW_PARITY_BLOCKED_AUDIT_ONLY`

Next phase:

`RECOVER_ORIGINAL_GENERATOR_AND_RAW_SNAPSHOT_OR_START_NEW_VERSIONED_RECONSTRUCTION`
