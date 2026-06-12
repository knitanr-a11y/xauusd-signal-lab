# GOLD V3 Stage107GE Spec — DUAL_EDGE_PORTFOLIO_SPLIT_STABILITY_AUDIT_ONLY

Created JST: `2026-06-12`

Stage:

```text
GOLD_V3_107GE_DUAL_EDGE_PORTFOLIO_SPLIT_STABILITY_AUDIT_ONLY
```

## Purpose

Stage107GD produced a diversified dual-edge candidate portfolio:

```text
LONG portfolio: 290 trades, WR 68.28%, PF 3.24, negative_month_count 0, candidate_count 1
SHORT portfolio: 228 trades, WR 61.84%, PF 2.79, negative_month_count 1, candidate_count 2
LONG/SHORT conflict: 0
```

Stage107GE tests whether this portfolio can be treated as a serious audit candidate pack, without approving live trading.

Stage107GE must evaluate:

```text
1. side-level stability
2. combined LONG+SHORT portfolio stability
3. 2025/2026 split stability
4. recent 2026-03-plus and 2026-05/06 stability
5. monthly negative count
6. candidate contribution and concentration risk
7. conflict-free operation without regime arbitration
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

Primary Stage107GD outputs:

```text
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_diversified_candidate_selection.csv
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_diversified_portfolio_ledger.csv
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_diversified_portfolio_summary.csv
FX_OUTPUTS/gold_v3/107gdc/gold_v3_107gd_long_short_portfolio_conflict.csv
```

Optional Stage107GB coverage:

```text
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_feature_coverage.csv
```

## Required outputs

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
gold_v3_107ge_side_portfolio_split_summary.csv
gold_v3_107ge_combined_portfolio_split_summary.csv
gold_v3_107ge_portfolio_monthly_summary.csv
gold_v3_107ge_candidate_contribution_summary.csv
gold_v3_107ge_stability_gate_matrix.csv
gold_v3_107ge_candidate_pack_audit.json
gold_v3_107ge_blocker_matrix.csv
gold_v3_107ge_validation_matrix.csv
gold_v3_107ge_summary.json
GOLD_V3_107GE_DUAL_EDGE_PORTFOLIO_SPLIT_STABILITY_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Stability gate defaults

Technical readiness remains separate from candidate acceptance.

Candidate pack audit gates:

```text
conflict_events == 0
combined_all_pf >= 1.80
combined_all_win_rate >= 0.55
combined_negative_month_count <= 2
LONG all PF >= 1.80
SHORT all PF >= 1.80
2025 PF >= 1.20 when trades >= 30
2026 PF >= 1.20 when trades >= 30
2026-03-plus PF >= 1.10 when trades >= 30
```

If gates fail, Stage107GE can still be READY but must mark candidate_pack_status as NEEDS_MORE_AUDIT.

## Status

READY:

```text
GOLD_V3_107GE_DUAL_EDGE_PORTFOLIO_SPLIT_STABILITY_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GE_DUAL_EDGE_PORTFOLIO_SPLIT_STABILITY_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
