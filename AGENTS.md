# Repository Agent Instructions

## GOLD_ML_V1

1. Use only the GOLD_ML_V1 namespace and its clean-rebuild contracts.
2. Do not use quarantined legacy GOLD logic or derived artifacts. Only explicitly authorized raw candle files are allowed.
3. Raw CSV `time` is bar-open time. Bar availability is open time plus timeframe duration. Never reinterpret this contract.
4. Preserve MT5 server timestamps. CSV latest rows are closed by contract.
5. Candidate logic is immutable. Changed logic requires a new ID.
6. The accumulated set contains nine audit-only entries: GML1-PROV-007, GML1-PROV-008, GML1-WATCH-022-B, GML1-PROV-010, GML1-PROV-015, GML1-PROV-020, GML1-WATCH-021-A, GML1-WATCH-021-B, GML1-WATCH-021-C.
7. GML1-WATCH-014-A, GML1-WATCH-022-A and GML1-WATCH-023-A remain research-only.
8. Read `config/gold_ml_v1/batch023_provenance_failure_20260625.json` and `config/gold_ml_v1/batch023_uploaded_raw_forensic_audit_20260625.json` before any Batch023 work.
9. The uploaded D1/H1/H4/M1/M5/M15 CSVs passed integrity audit: duplicate times 0, invalid OHLC 0, and every higher-timeframe OHLC row matches aggregation from M1.
10. The ZIP replay failed because it imposed one uniform indicator contract. The recovered contracts are lineage-specific.
11. M15-H4 recovery: H4 state spread/ATR uses simple TR14; H4 EMA40 slope/ATR uses Wilder ATR14; M15 trade and Bollinger ATR use simple TR14; M15 exits store M1 bar-close time.
12. H1-D1 recovery: H1 trade/spread ATR uses Wilder ATR14; D1 tick-volume ratio50 uses rolling median50; D1 delta3 uses Wilder ATR14; missing exact horizon minutes use the last available M1 close inside the horizon.
13. Post-warmup raw reconstruction is proven: PROV-007 153/154, PROV-008 168/169, WATCH-022-B 134/135 with zero extras and zero R mismatches; PROV-010 242/254 with zero extras, zero exit mismatches and zero R mismatches.
14. PROV-015, PROV-020 and WATCH-021-A/B/C filter membership reproduce exactly from their available parent decision registries.
15. The unresolved rows are only warmup-dependent: one M15-H4 decision at 2023-01-10 04:00 and twelve H1-D1 decisions in January 2023.
16. Full raw-only parity requires pre-2023 D1/H1/H4 history or serialized indicator seed state. Do not fill these rows silently from the exact registries.
17. Replay V1-V5 and the ZIP-bundled script are not original/exact replay tools and must not be described as such.
18. Historical raw input remains `gold_v3_2023_2026_*.csv`; live closed-bar observation remains `goldsharp_*.csv`. Never mix historical rows into new live decisions.
19. Same-lineage candidates are not independent edges and must not be summed as a portfolio.
20. The 2026 sample is diagnostic only and cannot be used for retuning.
21. Remain audit-only. No live activation, registration, automatic promotion, MT5 order, or Discord signal.
22. Never claim full raw parity until the pre-2023 warmup/state is recovered or a separately labeled warmup bridge is approved.

Current status:

`GOLD_ML_V1_015_BATCH023_CONTRACTS_RECOVERED_POST_WARMUP_PARITY_PROVEN_PRE2023_WARMUP_BLOCKED_AUDIT_ONLY`

Next phase:

`RECOVER_PRE2023_WARMUP_OR_BUILD_SEPARATELY_VERSIONED_WARMUP_BRIDGE_THEN_COST_STRESS`
