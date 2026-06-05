# GOLD V2 13E specification — MEDIUM feature/asof parity preflight audit-only

作成日: 2026-06-05  
repo: `knitanr-a11y/xauusd-signal-lab`  
工程名: `13E_MEDIUM_FEATURE_ASOF_PARITY_PREFLIGHT_AUDIT_ONLY`

---

## 1. 目的

13D3で `TIER2_HVT_RECONCILED_SOURCE_31` のaudit-only rule candidateはsource 31/31、final 13/13を満たした。

13Eでは、MEDIUM live化前のpreflightとして、source ledger上のfeature値をsource of truthにし、OHLCから再計算したcandidate featureが一致するかを監査する。

対象feature:

```text
range96
trend_eff96
ret96
tr_mean_32
regime
```

---

## 2. 重要方針

13Eはfeature parity監査であり、新規探索ではない。

```text
source rows / final rows = source of truth
OHLC = source feature値を再計算で再現できるかの検証入力
candidate formula = audit対象であり、通るまでlive formulaではない
```

candidate formulaが一致しない場合は停止し、live evaluatorには進めない。

---

## 3. 禁止

```text
OHLCから新規シグナル探索しない
不一致のcandidate formulaを採用しない
sourceにない条件を作らない
Discord通知しない
MT5発注しない
AI APIを呼ばない
live hookに接続しない
```

---

## 4. 入力

13D3出力:

```text
Files\FX_OUTPUTS\gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only\gold_v2_13d3_tier2_source_rows_with_reconciled_match.csv
Files\FX_OUTPUTS\gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only\gold_v2_13d3_tier2_final_rows_with_reconciled_match.csv
Files\FX_OUTPUTS\gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only\gold_v2_13d3_tier2_reconciled_rule_candidate.json
Files\FX_OUTPUTS\gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only\gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_summary.json
```

OHLC候補:

```text
goldsharp_m15.csv
xauusd_m15.csv
XAUUSD_M15.csv
candles_history_M15.csv
M15.csv
```

探索場所:

```text
repo root
Files root
Files\FX_OUTPUTS
```

---

## 5. strategy_id / entry_time / direction / TP-SL / outcome

```text
strategy_id:
  13D3 source rowsのstrategy_idを引き継ぐ

entry_time:
  13D3 source rowsのentry_timeを引き継ぐ

direction:
  13D3 source rowsのdirectionを引き継ぐ

TP/SL:
  再計算しない

outcome:
  profit_rをSOTとして引き継ぐ
```

---

## 6. candidate feature formula

13Eでは以下のcandidate formulaをaudit対象として計算する。

```text
range96 = rolling 96 high max - rolling 96 low min
ret96 = close - close.shift(96)
trend_eff96 = abs(ret96) / range96
tr = max(high-low, abs(high-prev_close), abs(low-prev_close))
tr_mean_32 = rolling 32 mean(tr)
regime = sourceと一致確認のみ。13Eではregime生成式を凍結しない。
```

このformulaがsource featureと一致しなければ、13Eは `FEATURE_PARITY_NOT_PROVEN` として停止する。

---

## 7. 期待件数

```text
source_rows = 31
final_rows = 13
m15_ohlc_found = true
feature rows at entry_time found = 31
```

feature一致は、以下を個別に判定する。

```text
range96
ret96
trend_eff96
tr_mean_32
```

---

## 8. 出力フォルダ

```text
Files\FX_OUTPUTS\gold_v2_13e_medium_feature_asof_parity_preflight_audit_only
```

---

## 9. 出力ファイル

```text
GOLD_V2_13E_MEDIUM_FEATURE_ASOF_PARITY_PREFLIGHT_AUDIT_ONLY_REPORT.md
gold_v2_13e_medium_feature_asof_parity_preflight_summary.json
gold_v2_13e_input_audit.csv
gold_v2_13e_ohlc_inventory.csv
gold_v2_13e_feature_formula_candidate_manifest.json
gold_v2_13e_source_rows_with_recomputed_features.csv
gold_v2_13e_feature_parity_by_row.csv
gold_v2_13e_feature_parity_summary.csv
gold_v2_13e_blockers.csv
gold_v2_13e_decision_matrix.csv
```

---

## 10. 成功条件

```text
13D3 status = TIER2_HVT_RECONCILED_RULE_CANDIDATE_FROZEN_AUDIT_ONLY
source rows = 31
final rows = 13
M15 OHLCが見つかる
entry_timeに対応するOHLC feature rowが31/31見つかる
range96 / ret96 / trend_eff96 / tr_mean_32 がsource値と許容誤差内で一致する
external actionsは全てfalse
```

---

## 11. 停止条件

```text
13D3出力がない
M15 OHLCが見つからない
entry_time対応が31/31にならない
feature一致が証明できない
regime生成式が未凍結
```

13Eでfeature一致が通っても、regime生成式とRANGE96/VOL_TRMEAN32を含むMEDIUM全体parityは別途監査する。

---

## 12. AI API

```text
AI APIを呼ばない
group評価をしない
component評価をしない
review-target allを使わない
```
