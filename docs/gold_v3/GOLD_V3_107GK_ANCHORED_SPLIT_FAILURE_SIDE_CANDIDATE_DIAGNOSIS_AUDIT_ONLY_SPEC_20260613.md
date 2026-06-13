# GOLD V3 Stage107GK Spec — ANCHORED_SPLIT_FAILURE_SIDE_CANDIDATE_DIAGNOSIS_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GK_ANCHORED_SPLIT_FAILURE_SIDE_CANDIDATE_DIAGNOSIS_AUDIT_ONLY
```

## Purpose

Stage107GJ showed only one anchored split passing the basic OOS gate:

```text
splits_passing_basic_oos_gate: 1
TRAIN_2025_TEST_2026 passed
TRAIN_2025H1_TEST_2025H2 failed
shorter 2026 splits had good PF/WR but too few trades
```

The user also suspects that both LONG and SHORT need additional independent edge vectors.

Stage107GK diagnoses whether failure is side-specific, candidate-specific, or vector-coverage related:

```text
1. For each anchored split, decompose test performance by side.
2. For each selected candidate, compare train statistics against test results.
3. Identify train-good / test-bad candidates.
4. Identify selected side gaps, especially LONG and SHORT missing-vector evidence.
5. If available, read Stage107GB candidate split summaries to surface post-hoc alternative vector hints.
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
軽: 数秒〜数分程度
1時間を超えたら停止して報告
```

Stage107GK primarily reads Stage107GJ outputs. It must not re-run full anchored grid search or read the full 107GB candidate ledger unless explicitly changed later.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107gjc/gold_v3_107gj_best_by_split.csv
FX_OUTPUTS/gold_v3/107gjc/gold_v3_107gj_selected_candidate_log.csv
FX_OUTPUTS/gold_v3/107gjc/gold_v3_107gj_best_selected_trade_ledger.csv
FX_OUTPUTS/gold_v3/107gjc/gold_v3_107gj_stability_summary.csv
```

Optional lightweight candidate summary:

```text
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_candidate_split_summary.csv
FX_OUTPUTS/gold_v3/107gbc/gold_v3_107gb_candidate_monthly_summary.csv
```

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107gkc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gkc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gk_split_side_test_summary.csv
gold_v3_107gk_selected_candidate_train_test_diagnosis.csv
gold_v3_107gk_failed_split_side_attribution.csv
gold_v3_107gk_vector_gap_recommendations.csv
gold_v3_107gk_posthoc_alternative_vector_hints.csv
gold_v3_107gk_quality_gate_matrix.csv
gold_v3_107gk_limitations.csv
gold_v3_107gk_recommended_next_actions.csv
gold_v3_107gk_blocker_matrix.csv
gold_v3_107gk_validation_matrix.csv
gold_v3_107gk_summary.json
GOLD_V3_107GK_ANCHORED_SPLIT_FAILURE_SIDE_CANDIDATE_DIAGNOSIS_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GK_ANCHORED_SPLIT_FAILURE_SIDE_CANDIDATE_DIAGNOSIS_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GK_ANCHORED_SPLIT_FAILURE_SIDE_CANDIDATE_DIAGNOSIS_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
