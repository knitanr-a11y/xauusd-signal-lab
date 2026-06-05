# GOLD V2 13I specification — patch preview live dry-run audit-only

作成日: 2026-06-05  
工程名: `13I_PATCH_PREVIEW_LIVE_DRY_RUN_AUDIT_ONLY`

## 1. 目的

13Hで作成した patch preview JSON を、実際の本番configへ反映せずに dry-run する。

13Iでは、patch preview の条件を再読込し、MEDIUM source ledger 上で期待件数を再現できるか、patch preview自体に安全フラグが入っているかを確認する。

## 2. 入力

```text
Files\FX_OUTPUTS\gold_v2_13h_medium_config_patch_preview_audit_only\gold_v2_13h_patch_preview.json
Files\FX_OUTPUTS\gold_v2_13h_medium_config_patch_preview_audit_only\gold_v2_13h_medium_config_patch_preview_summary.json
Files\FX_OUTPUTS\gold_v2_coreb_refined_probe_outputs\coreb_refined_rule_ledgers.csv
```

## 3. 成功条件

```text
patch_preview_only == true
do_not_apply_automatically == true
production config is not modified
TIER2_HVT selected rows == expected selected rows
missing/extra rows == expected 0
external actions false
```

## 4. 出力

```text
Files\FX_OUTPUTS\gold_v2_13i_patch_preview_live_dry_run_audit_only
```

```text
GOLD_V2_13I_PATCH_PREVIEW_LIVE_DRY_RUN_AUDIT_ONLY_REPORT.md
gold_v2_13i_patch_preview_live_dry_run_summary.json
gold_v2_13i_input_audit.csv
gold_v2_13i_dry_run_selected_rows.csv
gold_v2_13i_dry_run_checks.csv
gold_v2_13i_decision_matrix.csv
gold_v2_13i_blockers.csv
```

## 5. 禁止

```text
Discord通知しない
MT5発注しない
AI APIを呼ばない
live hookに接続しない
本番configを更新しない
```

## 6. 次工程

13Iが成功した場合でも、次は13Jのfinal approval gate audit-onlyであり、自動反映はしない。
