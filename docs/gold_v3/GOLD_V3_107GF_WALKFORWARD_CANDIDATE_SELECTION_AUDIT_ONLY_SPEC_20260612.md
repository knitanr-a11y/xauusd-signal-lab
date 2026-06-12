# GOLD V3 Stage107GF Spec — WALKFORWARD_CANDIDATE_SELECTION_AUDIT_ONLY

Created JST: `2026-06-12`

Stage:

```text
GOLD_V3_107GF_WALKFORWARD_CANDIDATE_SELECTION_AUDIT_ONLY
```

## Purpose

Stage107GE showed a strong in-sample diversified portfolio:

```text
combined trades: 518
combined win_rate: 65.44%
combined PF: 3.02
negative_month_count: 0
```

However, Stage107GE also intentionally includes selection-bias warning: selected candidates were chosen after looking at full-period audit outputs.

Stage107GF therefore performs **walk-forward candidate selection**:

```text
For each target month:
  1. Use only candidate trade results from months before the target month.
  2. Select LONG/SHORT candidates using only that prior history.
  3. Apply selected candidates to the target month.
  4. Aggregate out-of-sample monthly results.
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

## Important limitation

Stage107GF uses the Stage107GB candidate universe. That universe was generated from the full available OHLC period.

Therefore Stage107GF is stronger than full-period selection, because monthly candidate selection uses only prior results, but it is not yet a fully pure out-of-sample research protocol. A later train-only candidate-universe generation stage may still be required.

## Inputs

Primary input:

```text
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_top_candidate_trade_ledger.csv
```

Optional reference:

```text
FX_OUTPUTS/gold_v3/107gec/gold_v3_107ge_combined_portfolio_summary.csv
```

## Walk-forward search dimensions

```text
lookback_months: 3, 6, 12, expanding
min_train_trades: 20, 40, 80
min_train_pf: 1.50, 1.80, 2.00
min_train_wr: 0.50, 0.55, 0.60
max_train_negative_months: 1, 2
max_candidates_per_side: 1, 2, 4
max_train_overlap: 0.35
```

Each selected candidate must be selected separately for LONG and SHORT sides.

## Conflict handling

If selected LONG and SHORT candidates fire on the same entry timestamp in the target month:

```text
1. keep the side whose selected candidate had higher train_score
2. count the event as conflict_resolved_by_train_score
```

No regime arbitration is used in this stage.

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107gfc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gfc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gf_wf_config_summary.csv
gold_v3_107gf_wf_monthly_summary.csv
gold_v3_107gf_wf_selected_trade_ledger.csv
gold_v3_107gf_wf_selection_log.csv
gold_v3_107gf_wf_conflict_summary.csv
gold_v3_107gf_quality_gate_matrix.csv
gold_v3_107gf_selection_bias_warning.csv
gold_v3_107gf_blocker_matrix.csv
gold_v3_107gf_validation_matrix.csv
gold_v3_107gf_summary.json
GOLD_V3_107GF_WALKFORWARD_CANDIDATE_SELECTION_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GF_WALKFORWARD_CANDIDATE_SELECTION_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GF_WALKFORWARD_CANDIDATE_SELECTION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
