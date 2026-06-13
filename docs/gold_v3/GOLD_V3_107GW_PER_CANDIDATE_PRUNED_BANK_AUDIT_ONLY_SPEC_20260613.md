# GOLD V3 Stage107GW Spec — PER_CANDIDATE_PRUNED_BANK_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GW_PER_CANDIDATE_PRUNED_BANK_AUDIT_ONLY
```

## Purpose

The user clarified the target:

```text
勝率が高ければ、日に何十回とトレードがあってもよい。
勝率が低い候補をそのまま積むのではなく、各候補ごとに件数を削って勝率を上げる。
その高勝率化した候補を複数積み上げる。
```

Stage107GV showed that multi-vector bank configs can pass density2, but the best density2 configs were only around 56% to 58% win rate:

```text
density2_pass_count: 32
best_wr: 56.50%
best_pf: 2.18
best_density: 3.71/day
```

Stage107GW corrects the next step: prune each selected candidate individually using live-knowable entry-time calendar filters, then stack the pruned sub-candidates.

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

## Live-knowable pruning only

Allowed pruning dimensions:

```text
entry_dt hour
entry_dt day_of_week
entry_dt derived session bucket
```

Forbidden pruning dimensions:

```text
future TP/SL result
exit result
future high/low/close
future ATR/H4/D1
unresolved future horizon
open/incomplete candles
```

## Runtime estimate and progress

Expected runtime:

```text
軽〜中: 数分程度
1時間を超えたら停止して報告
```

The script must show percentage progress:

```text
progress 37.5% complete / 62.5% remaining | step x/y | split=... config=...
```

## Inputs

Required Stage107GV outputs:

```text
FX_OUTPUTS/gold_v3/107gvc/gold_v3_107gv_density2_pass_configs.csv
FX_OUTPUTS/gold_v3/107gvc/gold_v3_107gv_density2_candidate_composition.csv
```

Required Stage107GU output:

```text
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

For top density2 configs from 107GV:

1. Recover the selected candidate keys.
2. For each base candidate, generate pruned sub-candidates using train-only performance:
   - no prune baseline
   - hour bucket
   - session bucket
   - day-of-week bucket
   - session + day-of-week bucket
3. Keep only sub-candidates that pass train quality gates.
4. Stack the selected pruned sub-candidates.
5. Evaluate OOS portfolio after de-duplicating same entry time by train score.
6. No max trade-count penalty. More trades are acceptable if win rate and PF remain high.

## Desired gates

Primary high-volume/high-quality gate:

```text
OOS WR >= 60%
OOS PF >= 1.80
OOS business-day trade rate >= 2.0
OOS negative_month_count <= 2
```

Exploratory high-volume gate:

```text
OOS WR >= 58%
OOS PF >= 1.60
OOS business-day trade rate >= 2.0
OOS negative_month_count <= 3
```

## Outputs

```text
FX_OUTPUTS/gold_v3/107gwc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gwc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gw_input_coverage.csv
gold_v3_107gw_pruned_subcandidate_metrics.csv
gold_v3_107gw_pruned_bank_frontier.csv
gold_v3_107gw_best_pruned_bank_ledger.csv
gold_v3_107gw_selected_pruned_subcandidates.csv
gold_v3_107gw_quality_gate_matrix.csv
gold_v3_107gw_next_action_decision.csv
gold_v3_107gw_blocker_matrix.csv
gold_v3_107gw_validation_matrix.csv
gold_v3_107gw_summary.json
GOLD_V3_107GW_PER_CANDIDATE_PRUNED_BANK_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GW_PER_CANDIDATE_PRUNED_BANK_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GW_PER_CANDIDATE_PRUNED_BANK_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
