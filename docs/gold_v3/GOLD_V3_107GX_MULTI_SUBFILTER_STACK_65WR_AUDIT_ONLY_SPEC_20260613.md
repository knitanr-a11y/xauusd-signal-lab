# GOLD V3 Stage107GX Spec — MULTI_SUBFILTER_STACK_65WR_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GX_MULTI_SUBFILTER_STACK_65WR_AUDIT_ONLY
```

## Purpose

The user clarified the objective:

```text
勝率65%以上がほしい。
勝率が高ければ、日に何十回トレードがあってもかまわない。
勝率が低い候補をそのまま積むのではなく、各候補を削って勝率を上げ、その高勝率サブ候補を複数積む。
```

Stage107GW used only the single best prune per base candidate. It improved PF, but reduced density too much and did not reach 65% OOS WR:

```text
best_wr: 58.88%
best_pf: 2.405
best_density: 0.94/day
```

Stage107GX changes the selection model:

```text
From: one best subfilter per candidate
To: multiple high-win-rate subfilters per candidate, if they pass train-only quality
```

No upper trade-count penalty is used. More trades are allowed if WR/PF stay high.

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

## Live-knowable subfilters only

Allowed:

```text
entry hour
hour bucket / session
entry day-of-week
session + day-of-week
hour + day-of-week
```

Forbidden:

```text
future TP/SL
exit result
future high/low/close
future ATR/H4/D1 state
unresolved future horizon
open/incomplete candles
```

## Runtime estimate and progress

```text
medium; stop_if_over_1h
```

The script must print percent progress:

```text
progress 37.5% complete / 62.5% remaining | step x/y | ...
```

## Inputs

Required prior outputs:

```text
FX_OUTPUTS/gold_v3/107gvc/gold_v3_107gv_density2_pass_configs.csv
FX_OUTPUTS/gold_v3/107guc/gold_v3_107gu_selected_candidate_keys.csv
```

Exact candidate ledgers, if present:

```text
FX_OUTPUTS/gold_v3/107goc/gold_v3_107go_portfolio_ledger.csv
FX_OUTPUTS/gold_v3/107gnc/gold_v3_107gn_top_candidate_trade_ledger.csv
FX_OUTPUTS/gold_v3/107glc/gold_v3_107gl_top_vector_trade_ledger.csv
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_diversified_portfolio_ledger.csv
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_top_candidate_trade_ledger.csv
```

Do not scan broadly.

## Method

1. Load top Stage107GV density2 configs.
2. Recover selected candidate keys from Stage107GU.
3. For every base candidate, generate live-knowable subfilters.
4. Keep multiple subfilters per base candidate if they pass train-only thresholds.
5. Stack all accepted subfilters.
6. Deduplicate same entry_dt by train score.
7. Evaluate OOS.
8. Rank frontiers by OOS WR first, then PF and trade count.

## Selection profiles

```text
elite65_min6:
  train WR >= 0.65, train PF >= 1.50, train trades >= 6

elite65_min10:
  train WR >= 0.65, train PF >= 1.30, train trades >= 10

strict63_min10:
  train WR >= 0.63, train PF >= 1.60, train trades >= 10

wr60_pf2_min15:
  train WR >= 0.60, train PF >= 2.00, train trades >= 15
```

For each profile, select top subfilters by train score:

```text
N = 10, 20, 30, 50, 100, 200, 500
```

## OOS gates

Primary desired gate:

```text
OOS WR >= 0.65
OOS PF >= 1.50
OOS trades >= 30
```

High-volume 65 gate:

```text
OOS WR >= 0.65
OOS PF >= 1.50
OOS business-day trade rate >= 2.0
```

Fallback review gate:

```text
OOS WR >= 0.62
OOS PF >= 1.80
OOS trades >= 50
```

## Outputs

```text
FX_OUTPUTS/gold_v3/107gxc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gxc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gx_input_coverage.csv
gold_v3_107gx_subfilter_metrics.csv
gold_v3_107gx_stack_frontier.csv
gold_v3_107gx_best_stack_ledger.csv
gold_v3_107gx_selected_subfilters.csv
gold_v3_107gx_quality_gate_matrix.csv
gold_v3_107gx_next_action_decision.csv
gold_v3_107gx_blocker_matrix.csv
gold_v3_107gx_validation_matrix.csv
gold_v3_107gx_summary.json
GOLD_V3_107GX_MULTI_SUBFILTER_STACK_65WR_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GX_MULTI_SUBFILTER_STACK_65WR_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GX_MULTI_SUBFILTER_STACK_65WR_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
