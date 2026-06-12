# GOLD V3 Stage107GH Spec — FIXED_PORTFOLIO_STICKY_GATE_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GH_FIXED_PORTFOLIO_STICKY_GATE_AUDIT_ONLY
```

## Purpose

Stage107GG showed:

```text
fixed 107GE-style portfolio: PF 3.02 / WR 65.44%
walk-forward monthly reselection: PF 1.77 / WR 51.96%
WF candidate churn present: max side switches 11, unique selected candidates 24
SHORT weakened in WF: fixed PF 2.79 -> WF PF 1.54
conflict did not damage results materially
```

Stage107GH therefore tests a more conservative next idea:

```text
Do not reselect candidates every month.
Keep the fixed diversified 107GD/107GE small portfolio.
Use only prior-month history to optionally pause/resume portfolio, side, or candidate groups.
```

This tests whether sticky fixed candidates with a simple prior-history gate are better than unstable monthly reselection.

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

## Runtime estimate

Expected runtime:

```text
軽〜中: 数分〜20分程度
1時間を超えたら停止して軽量化確認
```

This stage reads existing fixed portfolio ledger and runs small monthly gate grids. It must not perform OHLC feature generation or full candidate search.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_diversified_portfolio_ledger.csv
```

Optional references:

```text
FX_OUTPUTS/gold_v3/107gec/gold_v3_107ge_combined_portfolio_summary.csv
FX_OUTPUTS/gold_v3/107ggc/gold_v3_107gg_failure_attribution.csv
```

## Gate modes

Stage107GH evaluates:

```text
no_gate_baseline
combined_monthly_gate
side_monthly_gate
candidate_monthly_gate
```

Definitions:

```text
combined_monthly_gate:
  For each target month, use prior months of the entire fixed portfolio.
  If pass, allow all fixed portfolio trades that month.

side_monthly_gate:
  For each target month and side, use prior months of that side.
  If pass, allow fixed portfolio trades for that side that month.

candidate_monthly_gate:
  For each target month and candidate, use prior months of that candidate.
  If pass, allow that candidate's fixed portfolio trades that month.
```

## Gate grid

```text
lookback_months: 3, 6, expanding
min_train_trades: 10, 20, 40
min_train_pf: 1.20, 1.50, 1.80, 2.00
min_train_wr: 0.50, 0.55, 0.60
max_train_negative_months: 0, 1, 2
```

## Important limitation

If fixed portfolio ledger does not contain `exit_dt`, Stage107GH uses prior **entry month** resolved results as a month-level audit proxy, not exact exit_dt live rehydration.

If `exit_dt` is present in future outputs, a later exact resolved-only gate can use `exit_dt <= current entry_dt`.

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107ghc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107ghc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gh_gate_config_summary.csv
gold_v3_107gh_best_gate_monthly_summary.csv
gold_v3_107gh_best_gate_side_summary.csv
gold_v3_107gh_best_gate_candidate_summary.csv
gold_v3_107gh_best_gate_selected_ledger.csv
gold_v3_107gh_gate_quality_matrix.csv
gold_v3_107gh_limitations.csv
gold_v3_107gh_recommended_next_actions.csv
gold_v3_107gh_blocker_matrix.csv
gold_v3_107gh_validation_matrix.csv
gold_v3_107gh_summary.json
GOLD_V3_107GH_FIXED_PORTFOLIO_STICKY_GATE_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GH_FIXED_PORTFOLIO_STICKY_GATE_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GH_FIXED_PORTFOLIO_STICKY_GATE_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
