# GOLD V2 13F specification — MEDIUM live eligibility matrix audit-only

作成日: 2026-06-05  
工程名: `13F_MEDIUM_LIVE_ELIGIBILITY_MATRIX_AUDIT_ONLY`

## 1. 目的

13D3でTIER2_HVTのreconciled rule candidateがsource/final replayを満たし、13E5でMEDIUM feature source chainが固定された。

13Fでは、MEDIUMをlive evaluatorへ進めるための条件を表に整理する。ただし13Fではlive許可を出さない。

## 2. 入力

```text
Files\FX_OUTPUTS\gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only\gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_summary.json
Files\FX_OUTPUTS\gold_v2_13e5_read_replay_feature_source_chain_audit_only\gold_v2_13e5_feature_source_chain_summary.json
Files\FX_OUTPUTS\gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only\gold_v2_13d3_tier2_reconciled_rule_candidate.json
configs\gold_v2\frozen_medium_rules_20260603.json
configs\gold_v2\live_evaluator_mapping_medium_20260603.json
```

## 3. 判定項目

```text
13D3 replay fixed
13E5 feature source chain fixed
external actions false
candidate rule remains audit-only
live config not updated by this step
live evaluator replay not yet proven
```

## 4. 期待結論

13Fの期待結論は以下。

```text
MEDIUM_LIVE_ELIGIBILITY_MATRIX_BUILT_AUDIT_ONLY_BLOCKED_PENDING_13G
```

13Fはlive許可ではなく、13Gでlive evaluator replayを作るための前提表である。

## 5. 出力

```text
Files\FX_OUTPUTS\gold_v2_13f_medium_live_eligibility_matrix_audit_only
```

```text
GOLD_V2_13F_MEDIUM_LIVE_ELIGIBILITY_MATRIX_AUDIT_ONLY_REPORT.md
gold_v2_13f_medium_live_eligibility_summary.json
gold_v2_13f_input_audit.csv
gold_v2_13f_eligibility_matrix.csv
gold_v2_13f_blockers.csv
gold_v2_13f_decision_matrix.csv
```

## 6. 禁止

```text
Discord通知しない
MT5発注しない
AI APIを呼ばない
live hookに接続しない
本番configを更新しない
```
