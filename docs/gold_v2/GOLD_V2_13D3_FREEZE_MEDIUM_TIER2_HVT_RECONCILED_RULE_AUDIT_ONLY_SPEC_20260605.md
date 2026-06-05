# GOLD V2 13D3 specification — freeze MEDIUM TIER2_HVT reconciled rule audit-only

作成日: 2026-06-05  
repo: `knitanr-a11y/xauusd-signal-lab`  
工程名: `13D3_FREEZE_MEDIUM_TIER2_HVT_RECONCILED_RULE_AUDIT_ONLY`

---

## 1. 目的

13D2で、TIER2_HVTのmanifest mismatchは単一原因 `tr_mean_32_min` で説明できることを確認した。

13D3では、13D2出力をsource of truthとして、TIER2_HVTのreconciled rule候補をaudit-onlyで凍結する。

これは本番configの書き換えではない。  
`configs/gold_v2/frozen_medium_rules_20260603.json` は変更しない。

---

## 2. 絶対禁止

```text
OHLCから新規探索しない
sourceにない条件を作らない
negative universe未監査のままlive許可しない
Discord通知しない
MT5発注しない
AI APIを呼ばない
live hookに接続しない
```

---

## 3. 入力CSV / JSON

13D3のsource of truthは13D2出力。

```text
Files\FX_OUTPUTS\gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only\gold_v2_13d2_medium_tier2_hvt_reconciliation_summary.json
Files\FX_OUTPUTS\gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only\gold_v2_13d2_tier2_source_rows.csv
Files\FX_OUTPUTS\gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only\gold_v2_13d2_tier2_final_sot_rows.csv
Files\FX_OUTPUTS\gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only\gold_v2_13d2_tier2_candidate_rule_manifest_patch_preview.json
Files\FX_OUTPUTS\gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only\gold_v2_13d2_tier2_expected_count_checks.csv
```

---

## 4. strategy_id / entry_time / direction / TP-SL / outcome

13D3でも新規トレード検出はしない。

```text
strategy_id:
  13D2 source rowsのstrategy_idを引き継ぐ

entry_time:
  13D2 source rowsのentry_timeを引き継ぐ

direction:
  13D2 source rowsのdirectionを引き継ぐ

TP/SL:
  再計算しない
  top_variant / selected_profit_r / profit_r をSOTとして扱う

outcome:
  profit_r > 0  => WIN
  profit_r < 0  => LOSS
  profit_r == 0 => BREAKEVEN
```

---

## 5. 13D3でfreezeする候補

13D2のpatch previewから、単一修正版候補を作る。

元条件:

```json
{
  "trend_eff96_max": 0.4,
  "ret96_max": -25.0,
  "tr_mean_32_min": 10.867578
}
```

候補条件:

```json
{
  "trend_eff96_max": 0.4,
  "ret96_max": -25.0,
  "tr_mean_32_min": 5.105624999999989
}
```

`tr_mean_32_min` は13D2 source 31件の最小値から決める。  
この値は13D2 source rowsのSOTであり、OHLCから新規に探索した値ではない。

---

## 6. 期待件数

13D3で必ず確認する期待件数:

```text
13D2 counts_ok = true
13D2 unique_failed_condition_sets = 1
original_manifest_source_match_rows = 19
reconciled_manifest_source_match_rows = 31
reconciled_manifest_source_extra_vs_source_rows = 0  # 13D2 source rows内でのextra
reconciled_manifest_final_match_rows = 13
final_rows = 13
```

注意:

```text
13D3は13D2 source rows内でのreplayであり、negative universe全体への拡張監査ではない。
extra_vs_source_rows=0 は source 31件の中だけの意味。
```

---

## 7. 監査方法

1. 13D2 summaryのstatus / counts_ok / unique_failed_condition_setsを読む。
2. 13D2 source rows 31件、final rows 13件を読む。
3. 元manifest条件をsource rowsに再適用し、19件一致を確認する。
4. patch previewのsource_31 envelopeからreconciled条件を作る。
5. reconciled条件をsource rowsに再適用し、31件一致を確認する。
6. reconciled条件をfinal rowsに再適用し、13件一致を確認する。
7. 差分条件、source/final成績、blockers、decision matrixを出力する。
8. audit-onlyのreconciled rule JSONを出すが、configは更新しない。

---

## 8. 出力フォルダ

```text
Files\FX_OUTPUTS\gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only
```

---

## 9. 出力ファイル

最初に見るファイル:

```text
GOLD_V2_13D3_FREEZE_MEDIUM_TIER2_HVT_RECONCILED_RULE_AUDIT_ONLY_REPORT.md
gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_summary.json
```

補助ファイル:

```text
gold_v2_13d3_input_audit.csv
gold_v2_13d3_tier2_reconciled_rule_candidate.json
gold_v2_13d3_tier2_reconciled_rule_candidate.csv
gold_v2_13d3_tier2_replay_checks.csv
gold_v2_13d3_tier2_source_rows_with_reconciled_match.csv
gold_v2_13d3_tier2_final_rows_with_reconciled_match.csv
gold_v2_13d3_tier2_rule_delta.csv
gold_v2_13d3_tier2_blockers.csv
gold_v2_13d3_tier2_decision_matrix.csv
```

---

## 10. 成功条件

```text
13D2 counts_ok = true
13D2 unique_failed_condition_sets = 1
reconciled rule候補がsource 31/31を満たす
reconciled rule候補がfinal 13/13を満たす
configは書き換えない
medium_live_evaluator_allowed=false
final_signal_allowed=false
Discord/MT5/AI/live_hook=false
```

---

## 11. 停止条件

```text
13D2出力が見つからない
13D2 counts_okがtrueでない
unique_failed_condition_setsが1でない
source rowsが31件でない
final rowsが13件でない
reconciled ruleがsource 31/31を満たさない
reconciled ruleがfinal 13/13を満たさない
```

停止した場合、live条件として扱わない。

---

## 12. AI API

```text
AI APIを呼ばない
group評価をしない
component評価をしない
review-target allを使わない
```

---

## 13. 実装ファイル

本体:

```text
scripts\gold_v2_runtime\audit_gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only.py
```

BAT:

```text
scripts\gold_v2_runtime\bat\13D3_AUDIT_FREEZE_MEDIUM_TIER2_HVT_RECONCILED_RULE_AUDIT_ONLY.bat
```

---

## 14. BAT実行順

```bat
scripts\gold_v2_runtime\bat\13D2_AUDIT_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY.bat
scripts\gold_v2_runtime\bat\13D3_AUDIT_FREEZE_MEDIUM_TIER2_HVT_RECONCILED_RULE_AUDIT_ONLY.bat
```

---

## 15. 実行してはいけないこと

```text
13D3のreconciled rule candidateを本番configとして扱わない
13D3完了だけでDiscord/MT5/live evaluatorをONにしない
13E feature/asof parityを飛ばさない
CoreB same_countを近似してHIGH arbitrationに混ぜない
```
