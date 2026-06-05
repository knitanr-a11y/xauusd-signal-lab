# GOLD V2 13E5 specification — read/replay feature source chain audit-only

作成日: 2026-06-05  
工程名: `13E5_READ_REPLAY_FEATURE_SOURCE_CHAIN_AUDIT_ONLY`

## 1. 目的

13E3でfeature値の完全一致source fileを発見した。13E4でcode candidateを探索したが、上位には13E4自身・仕様書のfalse positiveも混ざった。

13E5では、静的コード読解と実データjoinを組み合わせ、MEDIUM TIER2_HVT feature source chainを固定する。

## 2. 重要な切り分け

13E5はfeature生成式を新しく作らない。

```text
OK: 既存ledgerからfeature列がどの経路でSOTに渡ったかを固定する
NG: OHLCから近似式を作ってlive化する
```

## 3. 監査対象コード

```text
scripts/gold_v2_runtime/freeze_gold_v2_final_portfolio_sot_audit_only.py
scripts/gold_v2_runtime/audit_gold_v2_13b_corea_executable_mapping_freeze_audit_only.py
scripts/gold_v2_runtime/evaluate_gold_v2_coreA_coreB_medium_audit_only.py
```

## 4. 監査対象ledger

```text
Files\FX_OUTPUTS\gold_v2_coreb_refined_probe_outputs\coreb_refined_rule_ledgers.csv
Files\FX_OUTPUTS\gold_v2_coreb_refined_probe_outputs\coreb_refined_combined_ledgers.csv
Files\FX_OUTPUTS\gold_v2_ABC_stack_cap_2025_2026_validation_outputs\abc_stack_cap_2025_2026_portfolio_ledger.csv
Files\FX_OUTPUTS\gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only\gold_v2_13d3_tier2_source_rows_with_reconciled_match.csv
```

## 5. 成功条件

```text
13D3 TIER2 source 31 rowsが、coreb_refined_rule_ledgers または coreb_refined_combined_ledgers と entry_time/component/direction/feature値で完全一致する
freeze_gold_v2_final_portfolio_sot_audit_only.py がMEDIUMを coreb_refined_rule_ledgers から読むことを確認する
normalize_medium が range96 / trend_eff96 / ret96 / tr_mean_32 をpass-throughすることを確認する
```

## 6. 停止条件

```text
coreb_refined source ledgerがない
13D3 source 31件とMEDIUM source ledgerが完全一致しない
コード上でMEDIUM feature pass-throughが確認できない
```

## 7. 出力

```text
Files\FX_OUTPUTS\gold_v2_13e5_read_replay_feature_source_chain_audit_only
```

```text
GOLD_V2_13E5_READ_REPLAY_FEATURE_SOURCE_CHAIN_AUDIT_ONLY_REPORT.md
gold_v2_13e5_feature_source_chain_summary.json
gold_v2_13e5_input_audit.csv
gold_v2_13e5_medium_source_join_checks.csv
gold_v2_13e5_code_trace_checks.csv
gold_v2_13e5_decision_matrix.csv
gold_v2_13e5_blockers.csv
```

## 8. 禁止

```text
Discord通知しない
MT5発注しない
AI APIを呼ばない
live hookに接続しない
本番configへ反映しない
```
