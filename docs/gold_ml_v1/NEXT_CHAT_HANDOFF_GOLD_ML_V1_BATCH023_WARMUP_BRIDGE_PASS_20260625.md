# GOLD_ML_V1 Batch023 Warmup Bridge PASS — Next Chat Handoff

Date: 2026-06-25
Repository: `knitanr-a11y/xauusd-signal-lab`
Mode: **AUDIT ONLY**

## Current status

`GOLD_ML_V1_016_BATCH023_WARMUP_BRIDGE_9_OF_9_CORE_PARITY_PASS_AUDIT_ONLY`

## Do not redo

- Do not rerun V1-V5.
- Do not run the ZIP-bundled `replay_nine_candidates.py` as an original evaluator.
- Do not question whether raw CSV `time` is bar-open time. It is fixed as bar-open time in MT5 server time.
- Do not retune thresholds or candidate rules.

## Uploaded raw audit

The uploaded D1/H1/H4/M1/M5/M15 CSVs passed integrity checks:

- duplicate times: 0
- invalid OHLC rows: 0
- all higher-timeframe OHLC rows match aggregation from M1

Raw hashes:

- M1: `dec61b435ceb1df687baced57862de214793e0270e30c67d84f510f9f119b9d2`
- M15: `e327bedd180dae6429ed658ea714bc1229fb026262124248cdd5fff38fdeaa28`
- H1: `fb9d4ad228c02383a14ac86309f7306a799b0ef8d076f015a72b70daaddafc4a`
- H4: `5cd0d4427c752bd3feffd17b91fbd1ed3cd35ee5210887fa1726f01184367913`
- D1: `58d9b8e6716b3dedf4d310b3de5a914ab062c50578bae54dc85a2c8fddf689f6`

## Recovered lineage-specific contracts

### M15-H4

- H4 RCI18: rank-difference RCI on H4 close
- H4 state spread/ATR: spread price divided by simple rolling TR14
- H4 EMA40 slope6/ATR: EMA40 adjust=False divided by Wilder ATR14
- M15 trade ATR: simple rolling TR14
- M15 Bollinger: population std (`ddof=0`) divided by simple ATR14
- BB60 percentile100: fraction of trailing 100 values `<=` current
- event onset: false-to-true of `state AND eligibility` on full M15 sequence
- same-M1 priority: SL
- hit/time exit timestamp storage: M1 bar-close time

### H1-D1

- H1 BB60: population std (`ddof=0`)
- D1 RCI18: rank-difference RCI on D1 close
- H1 trade/spread ATR: Wilder ATR14
- D1 tick-volume ratio50: rolling median50, not mean
- D1 delta3/ATR: Wilder ATR14
- same-M1 priority: SL
- hit/time exit timestamp storage: M1 bar-open time
- when nominal horizon minute is unavailable, use the last available M1 close price inside the horizon

## Raw reconstruction before bridge

- PROV-007: 153/154, zero extra, zero exit/R mismatch
- PROV-008: 168/169, zero extra, zero exit/R mismatch
- WATCH-022-B: 134/135, zero extra, zero exit/R mismatch
- PROV-010: 242/254, zero extra, zero exit/R mismatch
- PROV-015: 213/225, zero extra, zero exit/R mismatch
- PROV-020: 193/204, zero extra, zero exit/R mismatch
- WATCH-021-A: 200/210, zero extra, zero exit/R mismatch
- WATCH-021-B: 197/207, zero extra, zero exit/R mismatch
- WATCH-021-C: 187/196, zero extra, zero exit/R mismatch

All missing rows are January 2023 warmup-dependent rows. There are no later missing rows and no extra rows.

## Warmup bridge result

A separately versioned warmup bridge was created. It marks every row as either:

- `RAW_RECONSTRUCTED`
- `WARMUP_BRIDGE_EXACT`

9/9 candidate core registries PASS:

- missing/extra: 0
- entry mismatch: 0
- exit mismatch: 0
- R mismatch: 0
- direction mismatch: 0

Bridge row counts:

| Candidate | Raw | Bridge | Total |
|---|---:|---:|---:|
| GML1-PROV-007 | 153 | 1 | 154 |
| GML1-PROV-008 | 168 | 1 | 169 |
| GML1-WATCH-022-B | 134 | 1 | 135 |
| GML1-PROV-010 | 242 | 12 | 254 |
| GML1-PROV-015 | 213 | 12 | 225 |
| GML1-PROV-020 | 193 | 11 | 204 |
| GML1-WATCH-021-A | 200 | 10 | 210 |
| GML1-WATCH-021-B | 197 | 10 | 207 |
| GML1-WATCH-021-C | 187 | 9 | 196 |

This is **not raw-only parity**. The bridge rows are historical audit rows only and must never emit live signals.

## Files created in the completed artifact

- `batch023_warmup_bridge_reconstruction.py`
- `warmup_bridge_parity_report.csv`
- `warmup_bridge_rows.csv`
- `warmup_bridge_summary.json`
- 9 `*_warmup_bridge_core_registry.csv`
- 9 `*_warmup_bridge_exact_schema_registry.csv`
- this handoff file

## Next phase

1. Commit the validated warmup-bridge script and output summary to GitHub if not already present.
2. Freeze status as audit-only.
3. Run spread stress 1.5x / 2.0x and fixed-slippage stress using **RAW_RECONSTRUCTED rows**; report bridge rows separately.
4. Then begin fresh prospective observation from goldsharp closed bars only.
5. No registration or live activation until cost stress and fresh observation pass.
