# NEXT CHAT HANDOFF ADDENDUM: GOLD V2 25C37 DONE -> 25C38 GUARDRAILS

Date: 2026-06-07
Repo: `knitanr-a11y/xauusd-signal-lab`
Primary handoff:

```text
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_25C37_DONE_25C38_NEXT_AUDIT_ONLY_20260607.md
```

This addendum exists to prevent the next chat from misreading 25C37 and moving too fast.

## Non-negotiable continuation rules

1. GOLD V2 remains **audit-only**.
2. 25C37 is already complete. Do **not** recreate 25C37.
3. Next step is **25C38 result review only**:

```text
25C38_COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_AUDIT_ONLY
```

4. 25C38 must not execute a new dry-run.
5. 25C38 must not mutate source files, rule conditions, configs, or source-of-truth artifacts.
6. 25C38 must not unblock CoreB live evaluator.
7. 25C38 must not create final signal, Discord notification, MT5 order, AI API call, live hook, or production evaluator path.
8. `REQUEST_MORE_AUDIT` is not source recovery approval.
9. Old GOLD / DISC8 remains quarantined.
10. Approximate reimplementation remains prohibited.

## 25C37 key result that must not be misread

25C37 result:

```text
Status: COREB_G1_ADJUSTED_NARROWING_DRY_RUN_COMPLETED_AUDIT_ONLY_RESULT_REVIEW_REQUIRED
best_variant: A003_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8_PAIR
best_left_only: 225
best_right_only: 200
best_both: 46
any_exact_match: false
CoreB live evaluator unblocked: false
```

Important interpretation:

- A003 is only the best variant by the script's current scoring among adjusted candidates.
- A003 is **not approved**, **not live-ready**, and **not a source-of-truth replacement**.
- A003 still over-narrows materially because right_only rises from 78 to 200 and both drops from 168 to 46.
- A002 and A004 are equivalent in 25C37: both 99, left_only 545, right_only 147.
- A001 is less destructive than A003 but still not exact: both 68, left_only 369, right_only 178.
- No candidate reached exact match.

## What 25C38 should do

25C38 should be a result-review script/report only.

Recommended inputs:

```text
FX_OUTPUTS/gold_v2_25c37_coreb_g1_adjusted_narrowing_dry_run_audit_only/02_25c37_coreb_g1_adjusted_narrowing_dry_run_summary.json
FX_OUTPUTS/gold_v2_25c37_coreb_g1_adjusted_narrowing_dry_run_audit_only/04_25c37_variant_filter_contract.csv
FX_OUTPUTS/gold_v2_25c37_coreb_g1_adjusted_narrowing_dry_run_audit_only/05_25c37_variant_compare_matrix.csv
FX_OUTPUTS/gold_v2_25c37_coreb_g1_adjusted_narrowing_dry_run_audit_only/06_25c37_variant_delta_matrix.csv
FX_OUTPUTS/gold_v2_25c37_coreb_g1_adjusted_narrowing_dry_run_audit_only/07_25c37_variant_by_dataset_policy.csv
FX_OUTPUTS/gold_v2_25c37_coreb_g1_adjusted_narrowing_dry_run_audit_only/09_25c37_acceptance_gate_matrix.csv
```

Recommended outputs:

```text
00_不要_25c38_file_request_list.csv
01_25c38_GOLD_V2_COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_AUDIT_ONLY_REPORT.md
02_25c38_coreb_g1_adjusted_narrowing_result_review_summary.json
03_25c38_input_audit.csv
04_25c38_adjusted_variant_tradeoff_matrix.csv
05_25c38_best_variant_review_matrix.csv
06_25c38_remaining_mismatch_decision_matrix.csv
07_25c38_next_step_plan.csv
```

Recommended status:

```text
COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_COMPLETED_AUDIT_ONLY_NEXT_PLAN_REQUIRED
```

## 25C38 decision framing

The next chat should not decide that A003 is good enough.

25C38 should explicitly evaluate:

- A003 reduces left_only most strongly but sacrifices too many target-matching keys.
- A001 may be a less destructive compromise, but still not exact.
- A002/A004 are less destructive than A003 but may not improve enough.
- The remaining mismatch likely needs either a new review plan or a different target-scope / right_only recovery audit, not live enabling.

## If local FX_OUTPUTS are not available

If the next environment cannot read local `FX_OUTPUTS`, ask the user only for the 25C37 required artifacts, not for unrelated old files:

```text
01_25c37_GOLD_V2_COREB_G1_ADJUSTED_NARROWING_DRY_RUN_AUDIT_ONLY_REPORT.md
02_25c37_coreb_g1_adjusted_narrowing_dry_run_summary.json
04_25c37_variant_filter_contract.csv
05_25c37_variant_compare_matrix.csv
06_25c37_variant_delta_matrix.csv
07_25c37_variant_by_dataset_policy.csv
09_25c37_acceptance_gate_matrix.csv
10_25c37_next_step_plan.csv
```

Do not request:

```text
00_不要_25c37_file_request_list.csv
full replay rows
full target rows
old 25C files unless needed for a specific cited reason
```

## Suggested next-chat prompt

```text
repo: knitanr-a11y/xauusd-signal-lab

まず以下を読んで続きからお願いします。

docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_25C37_DONE_25C38_NEXT_AUDIT_ONLY_20260607.md
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_25C37_DONE_25C38_NEXT_GUARDRAILS_ADDENDUM_20260607.md

GOLD V2は現在もaudit-onlyです。
REQUEST_MORE_AUDITはsource recovery承認ではありません。
旧GOLD/DISC8はHTF open-time不整合疑いで隔離済みです。
近似再実装は禁止です。
source-of-truthの監査済みartifactを優先してください。
Discord通知・MT5発注・AI API・live hook・live evaluator・final signalは明示許可までOFFです。
NO_SIGNAL時はDiscord通知しません。

25C37まで完了しました。
次は25C38_COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_AUDIT_ONLYです。
25C38は結果レビューのみで、dry-run再実行や条件変更はしないでください。
A003はbest_variantですが、採用・承認・live-readyではありません。
```
