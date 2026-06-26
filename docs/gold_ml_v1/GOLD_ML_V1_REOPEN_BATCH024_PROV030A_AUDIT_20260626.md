# GOLD_ML_V1 Batch024 / PROV-030-A reopened audit

Date: 2026-06-26

Status: `AUDIT_COMPLETE_NO_CANDIDATE_ACTIVATION`

Result record:

`config/gold_ml_v1/reopen_batch024_prov030a_multiview_audit_20260626.json`

## Scope

The user explicitly reopened Batch024 and `GML1-PROV-030-A` for renewed audit and wider exploration because the previous exploration or loss pruning may have been too coarse.

The existing accumulated nine were not modified. No new candidate was activated. Root BAT, live signals, MT5, Discord, AI API, health gate, automatic promotion and automatic registration remain unchanged and off.

The six RAW candle files matched their frozen SHA256 values. CSV `time` was treated as MT5 server bar-open time. Only higher-timeframe bars closed by the decision timestamp were joined. Same-M1 TP/SL collisions used SL priority.

2023 alone was used for exploration and shortlist selection. The frozen 2023 shortlist was then evaluated on 2024 validation, 2025 final test and 2026 diagnostics without retuning.

## Exact reproduction findings

### Batch024

The original 36 cells reproduced exactly:

- 2023 gate PASS: 4
- 2024 gate PASS: 17
- 2025 gate PASS: 15
- all-period survivors: 0

Therefore the old zero-survivor result was not an implementation error. However, the search was limited to an H1 EMA20/50 trend, an M15 RSI cross, optional EMA20 touch/reclose, and one fixed 1R/1.5R 12-hour exit. It was too narrow to reject the broader pullback space.

### GML1-PROV-030-A

The exact candidate also reproduced its recorded counts, PF and R values. It was not an implementation false negative. Its historical metrics remained strong in 2024 and 2025, but its final regime rule depended on a small 2023 H1 tree leaf and precise thresholds, so local-optimization risk remained.

## New multiview exploration

A predeclared 1,344-cell search covered 496 unique event sets across four views:

1. Expanded RSI/EMA pullback re-entry.
2. Structural pullback without mandatory RSI.
3. Trend-aligned compression breakout.
4. PROV-030-A decomposition, symmetric SHORT mirror and M5 confirmation variants.

Results:

- 225 cells met the 2023-only minimum requirements.
- 20 cells were frozen from 2023-only ranking.
- External evaluation: 4 `STRICT_PASS`, 1 `SOFT_WATCH`, 15 `FAIL`.

## Family findings

### P30 LONG family

All 6 audited neighboring cells passed both 2024 and 2025, showing that the historical edge was not isolated to one exact threshold. However, all 6 were negative in 2026 diagnostics. The family is historically valid but currently degraded. `GML1-PROV-030-A` is not reactivated and is not used as fallback or monitoring source.

### RPB LONG rejection family

2 of 8 neighboring cells passed 2024 and 2025, but both were negative in 2026. The plateau was narrow and current diagnostics were weak.

### STP SHORT structural-pullback family

6 of 36 neighboring cells passed 2024 and 2025, and all 6 were positive in 2026 diagnostics. This was the strongest genuinely different research direction.

The representative 2023-frozen rule used H4 bearish alignment, negative H1 EMA20 slope, an M15 EMA50 rejection/reclose and SHORT execution. Its results were:

- 2024: 69 resolved, PF 1.105, mean R 0.065
- 2025: 44 resolved, PF 1.385, mean R 0.227
- 2026 diagnostic: 65 resolved, PF 1.068, mean R 0.044

It remained positive in all six tested cost scenarios for 2024 and 2025. It also behaved differently from the P30 LONG and RPB LONG lineages.

## Decision

No exact new cell is promoted from this audit. The 2024, 2025 and 2026 results are now visible, so choosing the best exact threshold from them would violate the frozen-period contract.

The proper next direction is a new predeclared family-level STP SHORT contract or prospective audit-only observation that does not use external-period outcomes to select exact thresholds.

Current controls remain:

- existing nine unchanged
- active new candidates: 0
- Batch024 not activated as a candidate
- PROV-030-A not reactivated
- root BAT unchanged and status-only
- health gate OFF
- live-ready / final signal / MT5 / Discord OFF
