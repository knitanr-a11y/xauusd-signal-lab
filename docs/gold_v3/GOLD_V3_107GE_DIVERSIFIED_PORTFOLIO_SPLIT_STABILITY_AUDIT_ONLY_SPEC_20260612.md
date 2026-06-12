# GOLD V3 Stage107GE Spec — DIVERSIFIED_PORTFOLIO_SPLIT_STABILITY_AUDIT_ONLY

Created JST: `2026-06-12`

Stage:

```text
GOLD_V3_107GE_DIVERSIFIED_PORTFOLIO_SPLIT_STABILITY_AUDIT_ONLY
```

## Purpose

Stage107GD produced a diversified dual-edge portfolio:

```text
LONG portfolio: 290 trades, WR 68.28%, PF 3.24
SHORT portfolio: 228 trades, WR 61.84%, PF 2.79
LONG/SHORT conflict: 0 events
```

Stage107GE validates this combined portfolio by side, candidate, month, year, and recent split.

Important: Stage107GE is still in-sample/audit-only validation. It does not approve live use and does not remove the need for later walk-forward selection.

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

Primary Stage107GD outputs:

```text
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_diversified_candidate_selection.csv
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_diversified_portfolio_ledger.csv
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_diversified_portfolio_summary.csv
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_long_short_portfolio_conflict.csv
```

## Required analysis

Stage107GE must report:

```text
combined portfolio summary
side summary
candidate contribution summary
monthly summary
split summary: ALL / 2025 / 2026 / 2026-03-plus / 2026-05-06
conflict recheck from ledger
quality gate matrix
selection bias warning
```

## Quality gates

Default audit gates:

```text
combined trades >= 400
combined PF >= 2.00
combined win_rate >= 0.60
combined negative_month_count <= 2
per-side PF >= 2.00
per-side win_rate >= 0.55
conflict_events == 0
```

Gate failure is not a runtime rejection. It is an audit finding.

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107gec/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gec/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107ge_combined_portfolio_summary.csv
gold_v3_107ge_side_summary.csv
gold_v3_107ge_candidate_contribution.csv
gold_v3_107ge_monthly_summary.csv
gold_v3_107ge_split_summary.csv
gold_v3_107ge_conflict_recheck.csv
gold_v3_107ge_quality_gate_matrix.csv
gold_v3_107ge_selection_bias_warning.csv
gold_v3_107ge_blocker_matrix.csv
gold_v3_107ge_validation_matrix.csv
gold_v3_107ge_summary.json
GOLD_V3_107GE_DIVERSIFIED_PORTFOLIO_SPLIT_STABILITY_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GE_DIVERSIFIED_PORTFOLIO_SPLIT_STABILITY_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GE_DIVERSIFIED_PORTFOLIO_SPLIT_STABILITY_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
