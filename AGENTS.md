# Repository Agent Instructions

## GOLD_ML_V1

1. Use only the GOLD_ML_V1 namespace and its clean-rebuild contracts.
2. Do not use quarantined legacy GOLD logic or derived artifacts. Only explicitly authorized raw candle files are allowed.
3. Raw CSV `time` is bar-open time. Bar availability is open time plus timeframe duration. Never reinterpret this contract.
4. Preserve MT5 server timestamps. CSV latest rows are closed by contract.
5. Candidate logic is immutable. Changed logic requires a new ID.
6. The accumulated set contains nine audit-only entries: GML1-PROV-007, GML1-PROV-008, GML1-WATCH-022-B, GML1-PROV-010, GML1-PROV-015, GML1-PROV-020, GML1-WATCH-021-A, GML1-WATCH-021-B, GML1-WATCH-021-C.
7. GML1-WATCH-014-A, GML1-WATCH-022-A and GML1-WATCH-023-A remain research-only.
8. Read `config/gold_ml_v1/batch023_provenance_failure_20260625.json`, `config/gold_ml_v1/batch023_uploaded_raw_forensic_audit_20260625.json`, `config/gold_ml_v1/batch023_warmup_bridge_pass_20260625.json`, and `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_BATCH023_WARMUP_BRIDGE_PASS_20260625.md` before Batch023 work.
9. The uploaded D1/H1/H4/M1/M5/M15 CSVs passed integrity audit: duplicate times 0, invalid OHLC 0, and every higher-timeframe OHLC row matches aggregation from M1.
10. The ZIP replay failed because it imposed one uniform indicator contract. The recovered contracts are lineage-specific.
11. M15-H4 recovery: H4 state spread/ATR uses simple TR14; H4 EMA40 slope/ATR uses Wilder ATR14; M15 trade and Bollinger ATR use simple TR14; M15 hit/time exits store M1 bar-close time.
12. H1-D1 recovery: H1 trade/spread ATR uses Wilder ATR14; D1 tick-volume ratio50 uses rolling median50; D1 delta3 uses Wilder ATR14; H1-D1 hit/time exits store M1 bar-open time while time-exit price uses the last available M1 close inside the horizon.
13. Raw reconstruction is proven with zero extras and zero entry/exit/R/direction mismatch on all reproducible rows.
14. A separately versioned warmup bridge marks every row as `RAW_RECONSTRUCTED` or `WARMUP_BRIDGE_EXACT`.
15. Warmup bridge core parity passes 9/9 candidates with missing/extra 0, entry mismatch 0, exit mismatch 0, R mismatch 0, and direction mismatch 0.
16. Bridge counts: PROV-007 153+1, PROV-008 168+1, WATCH-022-B 134+1, PROV-010 242+12, PROV-015 213+12, PROV-020 193+11, WATCH-021-A 200+10, WATCH-021-B 197+10, WATCH-021-C 187+9.
17. `WARMUP_BRIDGE_EXACT` rows are historical audit rows only. They must never emit live signals and must be reported separately in stress tests.
18. This is not raw-only parity. Full raw-only parity still requires pre-2023 history or serialized indicator seed state.
19. Replay V1-V5 and the ZIP-bundled script are not original/exact replay tools and must not be described as such.
20. Historical raw input remains `gold_v3_2023_2026_*.csv`; live closed-bar observation remains `goldsharp_*.csv`. Never mix historical rows into new live decisions.
21. Same-lineage candidates are not independent edges and must not be summed as a portfolio.
22. The 2026 sample is diagnostic only and cannot be used for retuning.
23. Remain audit-only. No live activation, registration, automatic promotion, MT5 order, Discord signal, AI API, or live hook.
24. Next work is cost stress on `RAW_RECONSTRUCTED` rows with bridge rows shown separately, then fresh prospective goldsharp observation.

Current status:

`GOLD_ML_V1_016_BATCH023_WARMUP_BRIDGE_9_OF_9_CORE_PARITY_PASS_AUDIT_ONLY`

Next phase:

`COST_STRESS_RAW_RECONSTRUCTED_ONLY_REPORT_BRIDGE_SEPARATELY_THEN_FRESH_PROSPECTIVE`
