# GOLD V3 Stage107GB Spec — DUAL_EDGE_WALKFORWARD_DENSITY_AND_CONFLICT_AUDIT_ONLY

Created JST: `2026-06-12`

Stage:

```text
GOLD_V3_107GB_DUAL_EDGE_WALKFORWARD_DENSITY_AND_CONFLICT_AUDIT_ONLY
```

## Purpose

Stage107GB extends Stage107G because the first LONG/SHORT edge candidates looked promising but trade counts appeared low.

Stage107GB must answer:

```text
1. What exact period did the 107G OHLC input cover?
2. How many raw condition events existed before cooldown?
3. How many trades remained after cooldown 0/2/4?
4. Are results stable by month/year/split?
5. Do LONG edge and SHORT edge conflict at the same M15 close?
6. Does no-regime dual-edge remain viable without regime arbitration?
7. How do fixed RR2 and TP-min-5 / SL=TP/RR profiles compare?
```

## Guardrails

GOLD V3 remains audit-only.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 as trading sources.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime behavior, Stage69 runtime behavior, live evaluator, final signal, Discord, MT5 execution, or AI API.

CSV contract:

```text
open/in-progress candles are not written to CSV
CSV latest row is contractually closed
open/as-of treatment is forbidden
```

Pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```

## Inputs

Exact OHLC input directory:

```text
MQL5/Files/FX_INPUTS/gold_v3/107g/
```

Accepted exact filenames:

```text
gold#_m1.csv
gold#_m5.csv
gold#_m15.csv
gold#_h1.csv
gold#_h4.csv
gold#_d1.csv
goldsharp_m1.csv
goldsharp_m5.csv
goldsharp_m15.csv
goldsharp_h1.csv
goldsharp_h4.csv
goldsharp_d1.csv
```

If duplicate timestamps exist between live and 2025 files, Stage107GB must de-duplicate per timeframe and report duplicate counts.

## Candidate evaluation

Stage107GB uses closed OHLC only.

It must generate and evaluate:

```text
LONG edge candidates
SHORT edge candidates
one-clause, two-clause, and three-clause condition combinations
cooldown bars: 0, 2, 4
fixed RR2 profiles
TP-min-5 / SL=TP/RR profiles
```

Fixed profiles:

```text
TP5_SL2.5_RR2_H64
TP10_SL5_RR2_H64
TP15_SL7.5_RR2_H64
TP20_SL10_RR2_H64
```

Vol/RR profiles:

```text
TP = max(5.0, m15_atr28 * tp_mult)
SL = TP / rr
```

Grid:

```text
tp_mult: 0.50, 0.75, 1.00, 1.25
rr: 1.50, 2.00, 2.50, 3.00
```

No fixed 5 USD SL floor is allowed.

## Split reporting

Stage107GB must report metrics for:

```text
ALL
2025
2026
2026-03-plus
2026-05-06
```

If a split is absent, it must report zero trades rather than silently omit it.

## Required outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107gbc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gbc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gb_input_coverage.csv
gold_v3_107gb_feature_coverage.csv
gold_v3_107gb_candidate_density_summary.csv
gold_v3_107gb_candidate_split_summary.csv
gold_v3_107gb_candidate_monthly_summary.csv
gold_v3_107gb_top_candidates.csv
gold_v3_107gb_top_candidate_trade_ledger.csv
gold_v3_107gb_conflict_audit.csv
gold_v3_107gb_blocker_matrix.csv
gold_v3_107gb_validation_matrix.csv
gold_v3_107gb_summary.json
GOLD_V3_107GB_DUAL_EDGE_WALKFORWARD_DENSITY_AND_CONFLICT_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GB_DUAL_EDGE_WALKFORWARD_DENSITY_AND_CONFLICT_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GB_DUAL_EDGE_WALKFORWARD_DENSITY_AND_CONFLICT_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
