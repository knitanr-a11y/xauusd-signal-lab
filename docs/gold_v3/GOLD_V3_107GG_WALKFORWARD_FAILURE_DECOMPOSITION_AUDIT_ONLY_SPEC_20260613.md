# GOLD V3 Stage107GG Spec — WALKFORWARD_FAILURE_DECOMPOSITION_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GG_WALKFORWARD_FAILURE_DECOMPOSITION_AUDIT_ONLY
```

## Purpose

Stage107GE showed a strong full-period selected diversified portfolio:

```text
combined trades: 518
combined win_rate: 65.44%
combined PF: 3.02
negative_month_count: 0
```

Stage107GF walk-forward candidate selection fell to:

```text
trades: 612
win_rate: 51.96%
PF: 1.7678
negative_month_count: 0
quality gates: PASS 2 / FAIL 2
```

Stage107GG decomposes why the walk-forward result degraded:

```text
1. Did monthly re-selection choose weaker candidates?
2. Did LONG or SHORT degrade more?
3. Which months caused the PF/win-rate drop?
4. Did conflict resolution hurt performance?
5. Did fixed 107GE portfolio outperform walk-forward selection by month?
6. Is the issue candidate selection instability or candidate weakness?
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

## Runtime estimate

Expected runtime:

```text
軽〜中: 数分〜20分程度
1時間を超えたら停止して軽量化確認
```

This stage analyzes existing output ledgers and should not perform OHLC feature generation or full candidate search.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107gfc/gold_v3_107gf_wf_config_summary.csv
FX_OUTPUTS/gold_v3/107gfc/gold_v3_107gf_wf_selected_trade_ledger.csv
FX_OUTPUTS/gold_v3/107gfc/gold_v3_107gf_wf_selection_log.csv
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_top_candidate_trade_ledger.csv
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_diversified_portfolio_ledger.csv
```

Optional:

```text
FX_OUTPUTS/gold_v3/107gec/gold_v3_107ge_combined_portfolio_summary.csv
FX_OUTPUTS/gold_v3/107gec/gold_v3_107ge_monthly_summary.csv
FX_OUTPUTS/gold_v3/107gec/gold_v3_107ge_side_summary.csv
```

## Required analysis

### A. Fixed-vs-walk-forward comparison

Compare the fixed diversified 107GE/107GD portfolio against Stage107GF best walk-forward selected ledger.

Report:

```text
ALL summary
side summary
monthly summary
split summary
```

### B. Candidate churn diagnosis

For the Stage107GF best config, report:

```text
selected candidate count by side
months active per candidate
candidate switches month-to-month
average selected candidates per month
```

### C. Conflict impact

Reconstruct best walk-forward config raw selected candidate events from Stage107GB candidate ledger and Stage107GF selection log.

Compare:

```text
raw selected events before conflict resolution
resolved by train_score
conflict-only rows
drop-all-conflict scenario
```

### D. Failure attribution

Classify degradation into:

```text
FIXED_PORTFOLIO_BETTER
WF_SELECTION_CHURN_BAD
CONFLICT_DAMAGE
SIDE_SPECIFIC_WEAKNESS_LONG
SIDE_SPECIFIC_WEAKNESS_SHORT
CANDIDATE_UNIVERSE_OVERFIT_WARNING
```

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107ggc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107ggc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gg_fixed_vs_wf_summary.csv
gold_v3_107gg_fixed_vs_wf_monthly.csv
gold_v3_107gg_fixed_vs_wf_side.csv
gold_v3_107gg_wf_candidate_churn.csv
gold_v3_107gg_wf_conflict_impact.csv
gold_v3_107gg_failure_attribution.csv
gold_v3_107gg_recommended_next_actions.csv
gold_v3_107gg_blocker_matrix.csv
gold_v3_107gg_validation_matrix.csv
gold_v3_107gg_summary.json
GOLD_V3_107GG_WALKFORWARD_FAILURE_DECOMPOSITION_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GG_WALKFORWARD_FAILURE_DECOMPOSITION_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GG_WALKFORWARD_FAILURE_DECOMPOSITION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
