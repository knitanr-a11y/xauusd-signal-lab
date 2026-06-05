# GOLD V2 13E2 specification — MEDIUM feature formula/asof grid audit-only

作成日: 2026-06-05  
工程名: `13E2_MEDIUM_FEATURE_FORMULA_ASOF_GRID_AUDIT_ONLY`

## 1. 目的

13EでM15 OHLCとentry_timeは31/31で見つかったが、feature parityは未証明だった。

13E2では、OHLCからの新規探索ではなく、13D3/13E source rowsをsource of truthとして、feature式・asof位置の候補をグリッド診断する。

## 2. 入力

13D3:

```text
Files\FX_OUTPUTS\gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only\gold_v2_13d3_tier2_source_rows_with_reconciled_match.csv
Files\FX_OUTPUTS\gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only\gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_summary.json
```

13E:

```text
Files\FX_OUTPUTS\gold_v2_13e_medium_feature_asof_parity_preflight_audit_only\gold_v2_13e_medium_feature_asof_parity_preflight_summary.json
```

OHLC:

```text
goldsharp_m15.csv / xauusd_m15.csv / XAUUSD_M15.csv / candles_history_M15.csv / M15.csv
```

## 3. グリッド対象

```text
asof_shift_bars: -8..+8
ret_shift_bars: 90..102
range_window: 94..98
tr_mean_window: 30..34
tr_mode: true_range / high_low
```

sourceのentry_timeを固定し、candidate featureを各asof_shiftで照合する。

## 4. 出力

```text
Files\FX_OUTPUTS\gold_v2_13e2_medium_feature_formula_asof_grid_audit_only
```

主な出力:

```text
GOLD_V2_13E2_MEDIUM_FEATURE_FORMULA_ASOF_GRID_AUDIT_ONLY_REPORT.md
gold_v2_13e2_medium_feature_formula_asof_grid_summary.json
gold_v2_13e2_input_audit.csv
gold_v2_13e2_ohlc_inventory.csv
gold_v2_13e2_feature_best_variants.csv
gold_v2_13e2_joint_best_variants.csv
gold_v2_13e2_best_variant_row_diffs.csv
gold_v2_13e2_decision_matrix.csv
gold_v2_13e2_blockers.csv
```

## 5. 成功条件

```text
single joint variantが range96 / ret96 / trend_eff96 / tr_mean_32 を31/31再現する
```

成功してもlive化はしない。13E3で定義固定し、MEDIUM全体parityへ進む。

## 6. 停止条件

```text
OHLCが見つからない
source rowsが31件でない
feature完全一致variantがない
```

## 7. 禁止

```text
OHLCから新規シグナル探索しない
不一致variantを採用しない
Discord通知しない
MT5発注しない
AI APIを呼ばない
live hookに接続しない
```
