# GOLD V3 Stage107GN Spec — ATOMIC_VECTOR_DISCOVERY_V2_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GN_ATOMIC_VECTOR_DISCOVERY_V2_AUDIT_ONLY
```

## Purpose

Stage107GM showed that the Stage107GL new vector families are not viable:

```text
LONG practical_viable_count: 0
SHORT practical_viable_count: 0
LONG strict_viable_count: 0
SHORT strict_viable_count: 0
LONG exploratory_gap_fill_count: 0
SHORT exploratory_gap_fill_count: 0
quality_gates: FAIL 4
```

Main diagnosis:

```text
LONG: all 336 candidates are broken in 2026, and 298 are broken in 2025H2.
SHORT: 330/336 candidates are broken in 2026, 308 are broken in 2025H2, and 24 are single-year-only.
```

Therefore Stage107GN does not tune Stage107GL families. It redesigns vectors from smaller live-knowable atomic predicates.

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

The latest CSV row is contractually closed. Do not exclude it as open/as-of.

Pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```

## Runtime estimate

Expected runtime:

```text
中〜重: 30〜90分程度
1時間半を超えたら停止して報告
```

Stage107GN performs M5 TP/SL outcome evaluation, but limits seed generation before outcome evaluation.

## Inputs

Primary OHLC input directory:

```text
FX_INPUTS/gold_v3/107g/
```

Fallback exact MT5 Files root only:

```text
MQL5/Files/
```

Allowed exact filenames:

```text
gold#_m15.csv / goldsharp_m15.csv
gold#_m5.csv  / goldsharp_m5.csv
gold#_h1.csv  / goldsharp_h1.csv
gold#_h4.csv  / goldsharp_h4.csv
gold#_d1.csv  / goldsharp_d1.csv
```

No broad scan is allowed.

## Redesign principle

Stage107GL used named family variants that were still too broad or unstable.

Stage107GN uses atomic predicate groups:

```text
HTF context atoms
M15 trigger atoms
volatility atoms
session atoms
reversal/exhaustion atoms
range-position atoms
wick/body atoms
```

Each generated seed must include at least one trigger atom.

Examples:

```text
LONG trigger atoms:
  ema_reclaim_long
  failed_breakdown_reclaim
  lower_wick_reversal
  rsi_rebound_long
  breakout_hold_long
  momentum_reaccel_long

SHORT trigger atoms:
  ema_reject_short
  failed_breakout_reject
  upper_wick_reversal
  rsi_rollover_short
  breakdown_hold_short
  momentum_reaccel_short
```

## TP/SL profiles

Stage107GN uses a compact profile set to reduce runtime:

```text
TP5_SL2.5_RR2_H64
TP10_SL5_RR2_H64
TP15_SL7.5_RR2_H64
TPmax5_ATR0.50_RR1.5_H64
TPmax5_ATR0.75_RR2.0_H64
TPmax5_ATR1.00_RR2.0_H64
```

Dynamic rule:

```text
TP = max(5.0, m15_atr28 * atr_multiplier)
SL = TP / RR
```

Important:

```text
TP has a 5 USD minimum.
SL does not have a 5 USD minimum.
```

## Candidate filtering before M5 evaluation

Seed constraints:

```text
raw_events between 30 and 3500
forward_edge must be finite
max_seeds_per_side default: 70
```

Preselection score:

```text
forward_edge quality
raw_event sanity
side/family diversity
```

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107gnc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gnc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gn_input_coverage.csv
gold_v3_107gn_feature_coverage.csv
gold_v3_107gn_atomic_seed_summary.csv
gold_v3_107gn_candidate_summary.csv
gold_v3_107gn_top_long_candidates.csv
gold_v3_107gn_top_short_candidates.csv
gold_v3_107gn_top_candidate_trade_ledger.csv
gold_v3_107gn_family_summary.csv
gold_v3_107gn_split_summary.csv
gold_v3_107gn_quality_gate_matrix.csv
gold_v3_107gn_recommended_next_actions.csv
gold_v3_107gn_blocker_matrix.csv
gold_v3_107gn_validation_matrix.csv
gold_v3_107gn_summary.json
GOLD_V3_107GN_ATOMIC_VECTOR_DISCOVERY_V2_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Success indicators

Promising, not live-approved, if:

```text
At least one LONG candidate: trades >= 150, PF >= 2.0, WR >= 0.55, negative_month_count <= 2
At least one SHORT candidate: trades >= 150, PF >= 2.0, WR >= 0.55, negative_month_count <= 2
2026 PF >= 1.2 if 2026_trades >= 20
2025H2 PF >= 1.2 if 2025H2_trades >= 20
```

## Status

READY:

```text
GOLD_V3_107GN_ATOMIC_VECTOR_DISCOVERY_V2_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GN_ATOMIC_VECTOR_DISCOVERY_V2_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
