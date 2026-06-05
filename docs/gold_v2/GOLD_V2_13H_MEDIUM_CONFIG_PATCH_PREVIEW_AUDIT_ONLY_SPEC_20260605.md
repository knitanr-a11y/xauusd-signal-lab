# GOLD V2 13H specification — MEDIUM config patch preview audit-only

作成日: 2026-06-05  
工程名: `13H_MEDIUM_CONFIG_PATCH_PREVIEW_AUDIT_ONLY`

## 1. 目的

13Gで `TIER2_HVT` reconciled rule candidate が MEDIUM source ledger 上で31件ぴったり再現されることを確認した。

13Hでは、本番configを書き換えず、live evaluator mappingへ追加する場合のpatch previewだけを作る。

## 2. 入力

```text
Files\FX_OUTPUTS\gold_v2_13g_medium_live_evaluator_replay_audit_only\gold_v2_13g_medium_live_evaluator_replay_summary.json
Files\FX_OUTPUTS\gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only\gold_v2_13d3_tier2_reconciled_rule_candidate.json
configs\gold_v2\live_evaluator_mapping_medium_20260603.json
configs\gold_v2\frozen_medium_rules_20260603.json
```

## 3. 監査内容

1. 13G status が `MEDIUM_TIER2_HVT_LIVE_EVALUATOR_REPLAY_PROVEN_AUDIT_ONLY` であることを確認する。
2. 13D3 candidate rule conditions を読む。
3. 既存mapping/configがあれば読み取り、なければ `exists=false` として記録する。
4. 本番更新ではなく patch preview JSON を作る。

## 4. 出力

```text
Files\FX_OUTPUTS\gold_v2_13h_medium_config_patch_preview_audit_only
```

```text
GOLD_V2_13H_MEDIUM_CONFIG_PATCH_PREVIEW_AUDIT_ONLY_REPORT.md
gold_v2_13h_medium_config_patch_preview_summary.json
gold_v2_13h_input_audit.csv
gold_v2_13h_patch_preview.json
gold_v2_13h_rule_card.csv
gold_v2_13h_decision_matrix.csv
gold_v2_13h_blockers.csv
```

## 5. 成功条件

```text
13G replay proven
candidate conditions present
patch preview file created
external actions false
production config not modified
```

## 6. 禁止

```text
Discord通知しない
MT5発注しない
AI APIを呼ばない
live hookに接続しない
本番configを更新しない
```

## 7. 次工程

13H後に進める場合は、13Iでpatch previewを使ったlive evaluator dry-runを行う。
