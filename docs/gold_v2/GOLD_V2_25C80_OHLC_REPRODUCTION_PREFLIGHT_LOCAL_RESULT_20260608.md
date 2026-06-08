# GOLD V2 25C80 OHLC reproduction preflight local result

Created: 2026-06-08

Status: `OHLC_REPRODUCTION_PREFLIGHT_COMPLETED_AUDIT_ONLY`

This note records the local audit result produced from the uploaded candle files. It does not unlock live, final signal, MT5, Discord, AI, or source recovery.

## Result summary

- Candle files present: 12 / 12
- rr125 raw source-context rows checked: 16875
- rr125 profit/exit replay matches from M1 candles: 16871 / 16875
- rr125 replay mismatch rows: 4
- match ratio: 0.999762962962963
- A002 binding remains blocked by 25C79: 716 ambiguous events

## Feature parity snapshot

CoreB refined feature parity best variants:

- 2025 range96: `range96_inc`, exact 250 / 300
- 2025 adx14: `adx14_roll_inc`, exact 198 / 300
- 2026 range96: `range96_exc`, exact 194 / 195
- 2026 adx14: `adx14_wilder_exc`, exact 194 / 195

Interpretation: several OHLC-derived features can be reproduced under dataset/shift-specific conventions, but complete feature parity is not proven yet.

## Carry-forward blocker

`rr125_raw_signal_ledger.csv` source-context profit/exit is almost reproducible from M1 candles, but this does not identify which raw row belongs to each A002 event. A002 result use remains blocked until exact A002-to-raw identity binding is available.

## Next recommended step

`25C81_FORMULA_SOURCE_AND_FEATURE_PARITY_RECONCILIATION_AUDIT_ONLY`

Guardrails remain unchanged:

- GOLD V2 audit-only
- no source recovery approval
- no approximate reimplementation as SOT
- no Discord / MT5 / AI / live hook / final signal
