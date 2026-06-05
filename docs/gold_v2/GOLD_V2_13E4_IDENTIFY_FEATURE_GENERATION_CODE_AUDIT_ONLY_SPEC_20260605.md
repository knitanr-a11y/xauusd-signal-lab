# GOLD V2 13E4 specification — identify feature generation code audit-only

作成日: 2026-06-05  
工程名: `13E4_IDENTIFY_FEATURE_GENERATION_CODE_AUDIT_ONLY`

## 1. 目的

13E3で、TIER2_HVT source 31件のfeature値を完全一致で保持する既存ledgerが見つかった。

13E4では、そのledgerを作った生成コード候補をローカルから探す。

## 2. 13E3で見つかったfeature source

優先source:

```text
Files\FX_OUTPUTS\gold_v2_ABC_stack_cap_2025_2026_validation_outputs\abc_stack_cap_2025_2026_portfolio_ledger.csv
```

同じfeature値を持つ候補:

```text
Files\FX_OUTPUTS\gold_v2_coreb_refined_probe_outputs\coreb_refined_combined_ledgers.csv
Files\FX_OUTPUTS\gold_v2_13b_corea_executable_mapping_freeze_audit_only\gold_v2_13b_corea_source_cluster_ledger_normalized.csv
```

## 3. 監査対象

ローカルの以下を探索する。

```text
repo root
Files root
Files\FX_OUTPUTS
```

対象拡張子:

```text
.py
.bat
.ps1
.md
.json
.yaml
.yml
.txt
```

検索語:

```text
abc_stack_cap_2025_2026_portfolio_ledger.csv
gold_v2_ABC_stack_cap_2025_2026_validation_outputs
coreb_refined_combined_ledgers.csv
gold_v2_coreb_refined_probe_outputs
gold_v2_13b_corea_source_cluster_ledger_normalized.csv
range96
trend_eff96
ret96
tr_mean_32
```

## 4. 成功条件

```text
生成コード候補ファイルが見つかる
該当出力ledger名または出力フォルダ名を含む
feature列名を含む
```

## 5. 停止条件

```text
生成コード候補が見つからない
出力ファイル名との紐付けがない
feature列名だけで出力元が不明
```

## 6. 禁止

```text
コード候補を見つけただけでlive化しない
Discord通知しない
MT5発注しない
AI APIを呼ばない
live hookに接続しない
```

## 7. 出力

```text
Files\FX_OUTPUTS\gold_v2_13e4_identify_feature_generation_code_audit_only
```

```text
GOLD_V2_13E4_IDENTIFY_FEATURE_GENERATION_CODE_AUDIT_ONLY_REPORT.md
gold_v2_13e4_identify_feature_generation_code_summary.json
gold_v2_13e4_code_candidate_inventory.csv
gold_v2_13e4_code_candidate_hits.csv
gold_v2_13e4_best_code_candidate_snippets.csv
gold_v2_13e4_decision_matrix.csv
gold_v2_13e4_blockers.csv
```
