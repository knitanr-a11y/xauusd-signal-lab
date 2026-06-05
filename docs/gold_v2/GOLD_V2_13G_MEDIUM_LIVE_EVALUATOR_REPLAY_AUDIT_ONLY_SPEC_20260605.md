# GOLD V2 13G specification — MEDIUM live evaluator replay audit-only

作成日: 2026-06-05  
工程名: `13G_MEDIUM_LIVE_EVALUATOR_REPLAY_AUDIT_ONLY`

## 1. 目的

13Fで残った blocker は live evaluator replay 未証明である。

13Gでは、13D3で固定した TIER2_HVT reconciled rule candidate を、13E5で固定した MEDIUM feature source ledger に適用し、13D3 source 31件を再現できるかを監査する。

## 2. 入力

```text
Files\FX_OUTPUTS\gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only\gold_v2_13d3_tier2_source_rows_with_reconciled_match.csv
Files\FX_OUTPUTS\gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only\gold_v2_13d3_tier2_reconciled_rule_candidate.json
Files\FX_OUTPUTS\gold_v2_13e5_read_replay_feature_source_chain_audit_only\gold_v2_13e5_feature_source_chain_summary.json
Files\FX_OUTPUTS\gold_v2_coreb_refined_probe_outputs\coreb_refined_rule_ledgers.csv
configs\gold_v2\live_evaluator_mapping_medium_20260603.json
```

## 3. 監査内容

1. 13D3 source 31件をSOTとして読む。
2. 13D3 reconciled conditionを読む。
3. coreb_refined_rule_ledgers.csv の TIER2_HVT rows に条件を適用する。
4. entry_time / direction / component / feature値で 31件再現できるか確認する。
5. live evaluator mapping config は読み取り確認のみ。更新しない。

## 4. 成功条件

```text
candidate rule conditions are present
13E5 status is FEATURE_SOURCE_CHAIN_FIXED_AUDIT_ONLY
replay selected rows count == 31
source rows 31/31 are reproduced
no extra selected rows exist, or extras are explicitly reported as blocker
external actions false
```

## 5. 期待結論

成功しても本番許可はまだ出さない。

```text
MEDIUM_TIER2_HVT_LIVE_EVALUATOR_REPLAY_PROVEN_AUDIT_ONLY
```

次に 13H で config patch preview を作る。

## 6. 禁止

```text
Discord通知しない
MT5発注しない
AI APIを呼ばない
live hookに接続しない
本番configを更新しない
```

## 7. 出力

```text
Files\FX_OUTPUTS\gold_v2_13g_medium_live_evaluator_replay_audit_only
```

```text
GOLD_V2_13G_MEDIUM_LIVE_EVALUATOR_REPLAY_AUDIT_ONLY_REPORT.md
gold_v2_13g_medium_live_evaluator_replay_summary.json
gold_v2_13g_input_audit.csv
gold_v2_13g_replay_selected_rows.csv
gold_v2_13g_replay_diff_summary.csv
gold_v2_13g_decision_matrix.csv
gold_v2_13g_blockers.csv
```
