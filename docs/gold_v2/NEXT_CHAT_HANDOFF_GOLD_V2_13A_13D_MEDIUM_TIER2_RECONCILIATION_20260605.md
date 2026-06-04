# NEXT CHAT HANDOFF — GOLD V2 13A〜13D audit-only handoff

作成日: 2026-06-05  
対象repo: `knitanr-a11y/xauusd-signal-lab`  
現在位置: **13D完了 / 次は 13D-2 MEDIUM TIER2_HVT source definition reconciliation**  
重要方針: **AI API / Discord / MT5 / live hook はまだ全て禁止。audit-only継続。**

---

## 0. 最重要ルール

この会話では、GOLD V2 final portfolio SOT を live evaluator に落とすための監査を進めている。

絶対に守ること:

1. **近似実装禁止**
   - 探索済みSOTやsource ledgerを source of truth とする。
   - OHLCから再探索・再発見して、似た条件を作り直してはいけない。
   - `same_count` や `cluster_id` を「たぶんこうだろう」で近似してはいけない。

2. **audit-only**
   - Discord送信禁止。
   - MT5発注禁止。
   - AI API呼び出し禁止。
   - live hook接続禁止。
   - `final_signal_allowed=false` を維持。

3. **番号付き命名を維持**
   - ユーザーが「フォルダ名に13*が付いて分かりやすい」と明示。
   - 14以降も同じルールにする。

例:

```text
Files\FX_OUTPUTS\gold_v2_14a_xxxxx_audit_only
scripts\gold_v2_runtime\bat\14A_XXXXX_AUDIT_ONLY.bat
GOLD_V2_14A_XXXXX_AUDIT_ONLY_REPORT.md
gold_v2_14a_xxxxx_summary.json
```

4. **実行案内は必ずこの形で書く**
   - 実行BAT
   - 出力フォルダ
   - 最初に見るファイル
   - 補助で見るファイル

---

## 1. final portfolio SOT 現在の確定状態

Final SOT ledger:

```text
gold_v2_final_portfolio_2025_2026_sot_ledger.csv
```

確定行数:

```text
total = 529
2025 = 346
2026 = 183
```

source内訳:

```text
CORE_A_CORE_B_CONFLUENCE       8
CORE_A_ONLY                  317
CORE_B_ONLY                  117
MEDIUM_RANGE96_REFINED        51
MEDIUM_TIER2_HVT              13
MEDIUM_VOL_TRMEAN32_REFINED   23
```

最終成績:

```text
2025:
  count = 346
  WR    = 69.0751%
  PF    = 2.83905
  TotalR= +439.5091
  Worst = -5
  MaxDD = 19.20

2026:
  count = 183
  WR    = 72.1311%
  PF    = 3.65333
  TotalR= +248.75
  Worst = -5
  MaxDD = 7.00
```

現在も以下は全部 false:

```text
final_signal_allowed = false
step13_allowed = false
discord_send_allowed = false
mt5_order_allowed = false
ai_api_allowed = false
live_hook_allowed = false
```

---

## 2. 13A — final SOT to live evaluator gap audit

### GitHub追加

```text
scripts/gold_v2_runtime/audit_gold_v2_final_sot_to_live_evaluator_gap_audit_only.py
commit: ed32c891cc699683127c15def7fa1ad24cf89077

scripts/gold_v2_runtime/bat/13A_AUDIT_FINAL_SOT_TO_LIVE_EVALUATOR_GAP_AUDIT_ONLY.bat
commit: 8fc1cb09b3844dec48672724ef2abf60f6a7ed78
```

### 出力フォルダ

```text
Files\FX_OUTPUTS\gold_v2_13a_sot_to_live_evaluator_gap_audit_only
```

### 最初に見るファイル

```text
GOLD_V2_13A_SOT_TO_LIVE_EVALUATOR_GAP_AUDIT_ONLY_REPORT.md
gold_v2_13a_sot_to_live_evaluator_gap_summary.json
```

### 結論

```text
status = FINAL_SOT_READY_LIVE_EVALUATOR_BLOCKED_BY_GAPS_AUDIT_ONLY
sot_rows = 529
```

13Aでのcomponent status:

```text
FINAL_PORTFOLIO_SOT:
  READY
  row_count = 529
  NOT_A_LIVE_EVALUATOR
  final_signal_allowed = false

CORE_A:
  ROW_LEDGER_READY
  row_count = 325
  live_evaluator_status = BLOCKED_MAPPING_REQUIRED

CORE_B_RR125:
  SOURCE_RULES_AND_SOT_ROWS_READY
  row_count = 125
  live_evaluator_status = BLOCKED_FEATURE_AND_SAME_COUNT_PARITY_REQUIRED

MEDIUM:
  REFINED_RULE_ROWS_READY
  row_count = 87
  live_evaluator_status = BLOCKED_HIGH_ARBITRATION_AND_FEATURE_PARITY_REQUIRED

EXTERNAL_ACTIONS:
  OFF
  DISABLED_BY_POLICY
```

主要ブロッカー:

```text
B001 CORE_A:
  live CoreA signal requires executable fold4_rules + ABC gate + CAP5/CAP3 mapping.

B002 CORE_A:
  A_CAP5_BC_CAP3 sizing needs live-computable mapping.

B003 CORE_B:
  same_count_source_hit_count >= 15 parity must be proven.

B004 CORE_B:
  CoreB feature formulas / M15-M5 asof timing must be proven.

B005 MEDIUM:
  direction, TIER2_HVT, CoreA_REJECT, high arbitration must be implemented exactly.

B006 GLOBAL:
  dry-run parity and preflight required before signal output.

B007 SAFETY:
  external actions need explicit future permission only after all gates pass.
```

---

## 3. 13B — CoreA executable mapping freeze audit

### GitHub追加

```text
scripts/gold_v2_runtime/audit_gold_v2_13b_corea_executable_mapping_freeze_audit_only.py
commit: e16001027d98742a6b964e7faff01d3a62fef6ac

scripts/gold_v2_runtime/bat/13B_AUDIT_COREA_EXECUTABLE_MAPPING_FREEZE_AUDIT_ONLY.bat
commit: 2ca6fcfdcb23670d6f672225dfa4cd5ab32ac1e1
```

### 出力フォルダ

```text
Files\FX_OUTPUTS\gold_v2_13b_corea_executable_mapping_freeze_audit_only
```

### 結論

```text
status = COREA_SOT_READY_EXECUTABLE_MAPPING_BLOCKED_AUDIT_ONLY
corea_sot_rows = 325
corea_source_selected_rows = 325
```

CoreA内訳:

```text
A       = 173
C_fixed = 124
B_rr15  = 28
```

CoreA再集計:

```text
2025:
  count = 200
  WR    = 65.50%
  PF    = 2.37904
  TotalR= +230.242R

2026:
  count = 125
  WR    = 73.60%
  PF    = 3.80435
  TotalR= +193.50R
```

判定:

```text
B_rr15:
  regime == MID_MIXED
  trend_eff96 >= 0.633155
  rr >= 1.5
  source上では照合可能
  ただし live feature parity と CoreA rejected 順序が必要

C_fixed:
  100.43 <= range96 <= 117.86
  source上では照合可能
  ただし live range96 parity と CoreA rejected 順序が必要

A:
  is_A flag はある
  ただし tail_hard / top5 / all-consensus / stack KEEP の実行可能条件が未凍結
```

CoreA最大ブロッカー:

```text
Aゲートが未凍結。
B/Cは比較的近いが、A/fold4 mappingがないため CoreA live evaluator はまだ禁止。
```

---

## 4. 13C — CoreB feature / same_count parity audit

### GitHub追加

```text
scripts/gold_v2_runtime/audit_gold_v2_13c_coreb_feature_same_count_parity_audit_only.py
commit: f3f4363eacbe27a1a3b2788697b4cffd1bdb9d56

scripts/gold_v2_runtime/bat/13C_AUDIT_COREB_FEATURE_SAME_COUNT_PARITY_AUDIT_ONLY.bat
commit: b46a56d54e525ac5216b7e7e4b4e5aac6b6543f6
```

### 出力フォルダ

```text
Files\FX_OUTPUTS\gold_v2_13c_coreb_feature_same_count_parity_audit_only
```

### 結論

CoreB定義自体は揃っている:

```text
selected_rule_count = 12
same_count_source_rule_count = 33
selected_condition_count = 65
same_count_source_condition_count = 181
required_field_count = 38
condition_fields_missing_from_required_fields = []
```

standalone CoreB source成績:

```text
2025:
  count = 104
  WR    = 72.1154%
  PF    = 3.44351
  TotalR= +143.017R

2026:
  count = 21
  WR    = 80.9524%
  PF    = 5.15385
  TotalR= +40.5R
```

ただし parity は未証明:

```text
candidate_replay_signal_rows = 7
expected historical standalone CoreB rows = 125
parity_status = NOT_PROVEN_CANDIDATE_FORMULA_ONLY
```

結論:

```text
12 selected rules / 33 same_count source rules / 38 feature列は揃っている。
しかし live式として replay すると 125件ではなく7件しか出ない。
```

---

## 5. 13C-2 — CoreB source ledger to feature snapshot parity audit

### GitHub追加

```text
scripts/gold_v2_runtime/audit_gold_v2_13c2_coreb_source_ledger_to_feature_snapshot_parity_audit_only.py
commit: 944344a9da1f51b97fa522be63bb1cce2d26ae6f

scripts/gold_v2_runtime/bat/13C2_AUDIT_COREB_SOURCE_LEDGER_TO_FEATURE_SNAPSHOT_PARITY_AUDIT_ONLY.bat
commit: d3cfeffc145b423eadbb915b3094b43d743d8e49
```

### 出力フォルダ

```text
Files\FX_OUTPUTS\gold_v2_13c2_coreb_source_ledger_to_feature_snapshot_parity_audit_only
```

### 結論

```text
status = COREB_SOURCE_LEDGER_TO_FEATURE_SNAPSHOT_PARITY_FAILED_ROOT_CAUSE_IDENTIFIED_AUDIT_ONLY
target_rows = 125
feature_exact_match_rows = 109
feature_missing_rows = 16
candidate_replay_global_signal_rows = 7
candidate_signal_at_exact_source_entry_rows = 1
candidate_signal_pm180_target_rows = 5
```

主因:

```text
source same_count median = 22
replay same_count median = 7
```

つまり `same_count` は単一feature行で33 same_count source rulesを何個hitしたかではない。

試した仮説:

```text
source same_count == raw exact entry_time count        -> 一致 0件
source same_count == interval cover count             -> 一致 3件
source same_count == connected interval component size -> 一致 10件
```

結論:

```text
same_count は探索時の cluster/confluence membership semantics に近い。
現状の candidate formula replay は source parity ではない。
```

---

## 6. 13C-3 — CoreB reconstruct source cluster membership audit

### GitHub追加

```text
scripts/gold_v2_runtime/audit_gold_v2_13c3_coreb_reconstruct_source_cluster_membership_audit_only.py
commit: 43a155e3edd3e3d8b557434194b11273da1467d2

scripts/gold_v2_runtime/bat/13C3_AUDIT_COREB_RECONSTRUCT_SOURCE_CLUSTER_MEMBERSHIP_AUDIT_ONLY.bat
commit: 3f7bf014dc73ca6ff5d074774e678505252a5ef2
```

### 出力フォルダ

```text
Files\FX_OUTPUTS\gold_v2_13c3_coreb_reconstruct_source_cluster_membership_audit_only
```

### 結論

```text
status = COREB_SOURCE_CLUSTER_MEMBERSHIP_RECONSTRUCTION_FAILED_ORIGINAL_ALGORITHM_REQUIRED_AUDIT_ONLY
target_rows = 125
source_top_cluster_inventory_rows = 287
rr125_raw_signal_rows = 6834
```

raw ledgerだけで試した最良の再構成:

```text
best_static_window_algorithm = entry_window_center_90m
exact_same_count_rows = 34 / 125
within1_rows = 41 / 125
within3_rows = 58 / 125
MAE = 10.136
```

connected component:

```text
connected_component_exact_same_count_rows = 10 / 125
```

結論:

```text
raw ledgerだけでは cluster membership / same_count を完全再構成できない。
top_ledgers には cluster summary はあるが、row-level membership が無い。
original clustering algorithm か cluster membership ledger が必要。
```

---

## 7. 13C-4 — CoreB original clustering script search audit

### GitHub追加

```text
scripts/gold_v2_runtime/audit_gold_v2_13c4_coreb_original_clustering_script_search_audit_only.py
commit: d71111bbf742a9a3f8e6ae48280d7aa0cffa52aa

scripts/gold_v2_runtime/bat/13C4_AUDIT_COREB_ORIGINAL_CLUSTERING_SCRIPT_SEARCH_AUDIT_ONLY.bat
commit: d328a5a0d25c1ca71dd5fb6381595d5bf3595f2d
```

### 出力フォルダ

```text
Files\FX_OUTPUTS\gold_v2_13c4_coreb_original_clustering_script_search_audit_only
```

### 結論

13C-4の初回検索では候補が出た:

```text
original_algorithm_candidate_files = 10
same_count_source_universe_freeze_hit_files = 2
```

ただし、これはkeyword scoreでの候補なので **深掘りレビューが必要** となった。

次推奨:

```text
13C5_REVIEW_RESTORED_CLUSTERING_SCRIPT_PARITY_AUDIT_ONLY
```

---

## 8. 13C-5 — CoreB clustering candidate review audit

### GitHub追加

```text
scripts/gold_v2_runtime/audit_gold_v2_13c5_review_restored_clustering_script_parity_audit_only.py
commit: c7e6b2c306540a81153663c0d72f86b26277a965

scripts/gold_v2_runtime/bat/13C5_AUDIT_REVIEW_RESTORED_CLUSTERING_SCRIPT_PARITY_AUDIT_ONLY.bat
commit: 96326fbb20bdb5d172756bd6698a208e94f91817
```

### 出力フォルダ

```text
Files\FX_OUTPUTS\gold_v2_13c5_coreb_review_restored_clustering_script_parity_audit_only
```

### 結論

13C-4の候補10件を厳格判定した結果:

```text
status = COREB_ORIGINAL_CLUSTERING_SCRIPT_NOT_CONFIRMED_COREB_LIVE_BLOCKED_AUDIT_ONLY
reviewed_keyword_hit_files = 62
true_original_clustering_candidate_files = 0
```

分類:

```text
AUDIT_GENERATED_OR_POST_HOC                         8
MENTIONS_KEYWORDS_ONLY                             20
SOT_READER_ONLY                                     3
SOURCE_DEFINITION_OR_DOC                           30
SOURCE_UNIVERSE_RULE_FREEZE_NOT_CLUSTER_MEMBERSHIP  1
```

決定:

```text
CoreB historical SOT = ALLOWED
CoreB live evaluator = BLOCKED
Approximate same_count = FORBIDDEN
```

次推奨:

```text
13D_MEDIUM_FEATURE_ARBITRATION_AUDIT_ONLY
```

---

## 9. 13D — MEDIUM feature / arbitration audit

### GitHub追加

```text
scripts/gold_v2_runtime/audit_gold_v2_13d_medium_feature_arbitration_audit_only.py
commit: c813056a9e929d5a0a2eca7200aaee80c305259e

scripts/gold_v2_runtime/bat/13D_AUDIT_MEDIUM_FEATURE_ARBITRATION_AUDIT_ONLY.bat
commit: 8d53b7c315ad0ef763643d9787a48a1e53dcdeec
```

### 出力フォルダ

```text
Files\FX_OUTPUTS\gold_v2_13d_medium_feature_arbitration_audit_only
```

### 最初に見るファイル

```text
GOLD_V2_13D_MEDIUM_FEATURE_ARBITRATION_AUDIT_ONLY_REPORT.md
gold_v2_13d_medium_feature_arbitration_summary.json
```

### 補助で見るファイル

```text
gold_v2_13d_input_audit.csv
gold_v2_13d_medium_rule_manifest_inventory.csv
gold_v2_13d_medium_rule_manifest_coverage.csv
gold_v2_13d_medium_arbitration_replay_checks.csv
gold_v2_13d_medium_arbitration_summary.csv
gold_v2_13d_medium_final_sot_rule_summary.csv
gold_v2_13d_medium_source_rows_with_manifest_match.csv
gold_v2_13d_medium_selected_after_internal_priority.csv
gold_v2_13d_medium_dropped_by_internal_priority.csv
gold_v2_13d_medium_recomputed_final_rows.csv
gold_v2_13d_medium_blocked_by_high_arbitration.csv
gold_v2_13d_medium_blockers.csv
```

### 結論

```text
status = MEDIUM_ARBITRATION_REPLAY_MATCHES_SOT_BUT_TIER2_MANIFEST_MISMATCH_AUDIT_ONLY
medium_source_rows = 118
medium_internal_priority_selected_rows = 87
medium_internal_priority_dropped_rows = 31
medium_final_sot_rows = 87
arbitration_replay_matches_final_sot = true
```

arbitration replay checks:

```text
final_medium_rows                 87 / 87 OK
recomputed_medium_rows            87 / 87 OK
missing_final_keys_in_recomputed   0 / 0  OK
extra_recomputed_keys_not_in_final 0 / 0  OK
blocked_by_high_rows               0 / 0  OK
internal_priority_dropped_rows    31 / 31 OK
```

MEDIUM内訳:

```text
RANGE96_REFINED:
  source_rows = 51
  final_rows = 51
  WR = 72.549%
  PF = 3.69444
  TotalR = +48.5

VOL_TRMEAN32_REFINED:
  source_rows = 36
  internal_priority_selected_rows = 23
  internal_priority_dropped_rows = 13
  final_rows = 23
  WR = 69.5652%
  PF = 3.1
  TotalR = +21

TIER2_HVT:
  source_rows = 31
  internal_priority_selected_rows = 13
  internal_priority_dropped_rows = 18
  final_rows = 13
  WR = 76.9231%
  PF = 12
  TotalR = +22
```

manifest coverage:

```text
RANGE96_REFINED:
  manifest_match_rows = 51 / 51
  manifest_mismatch_rows = 0

VOL_TRMEAN32_REFINED:
  manifest_match_rows = 36 / 36
  manifest_mismatch_rows = 0

TIER2_HVT:
  source_rows = 31
  manifest_match_rows = 19
  manifest_mismatch_rows = 12
  manifest_match_pct = 61.2903%
```

Final SOT上のTIER2:

```text
TIER2_HVT final_rows = 13
manifest_match_rows_in_final = 2
manifest_mismatch_rows_in_final = 11
```

つまり:

```text
MEDIUM arbitration再現はOK。
しかし frozen_medium_rules_20260603.json の TIER2_HVT 定義がsource実績とズレている。
```

13Dブロッカー:

```text
13D-B001:
  TIER2_HVT live rule definition
  TIER2_HVT manifest mismatch rows=12
  reconcile frozen_medium_rules_20260603.json with source ledger or split Tier2 variants.

13D-B002:
  feature formula/asof parity
  Prove range96/trend_eff96/ret96/tr_mean_32/regime live feature formulas match source snapshot at confirmed M15 close.

13D-B003:
  HIGH arbitration dependency
  Final MEDIUM eligibility requires CoreA/CoreB live candidate arbitration.
  CoreB is currently historical-only/live-blocked.

13D-B004:
  external actions stay disabled.
```

次推奨:

```text
13D2_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY
```

---

## 10. 現在の未解決ブロッカーまとめ

### CoreA

```text
CoreA historical SOT = ready
CoreA live evaluator = blocked
```

未解決:

```text
A gate:
  tail_hard / top5 / all-consensus / stack KEEP が未凍結

B/C:
  formulas are partially executable, but need live feature/asof parity and CoreA rejected ordering
```

### CoreB

```text
CoreB historical SOT = allowed
CoreB live evaluator = blocked
```

未解決:

```text
same_count / cluster_id:
  original clustering algorithm not found
  row-level membership ledger missing
  raw ledger approximation fails
  live same_count approximation forbidden
```

### MEDIUM

```text
MEDIUM historical SOT replay = OK
MEDIUM live evaluator = blocked
```

未解決:

```text
TIER2_HVT manifest mismatch:
  source rows 31中 12件不一致
  final SOT TIER2 13件中 11件不一致

feature/asof parity:
  range96 / trend_eff96 / ret96 / tr_mean_32 / regime の live計算一致が未証明

HIGH dependency:
  CoreA/CoreB live arbitrationが未完成
```

---

## 11. 次チャットで最初にやること

次はこれ。

```text
13D2_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY
```

目的:

```text
TIER2_HVTのsource 31件を、manifest match / mismatch に分ける
final SOTに残ったTIER2 13件のうち、11件がなぜmanifest外なのか特定
TIER2_HVTが1条件ではなく複数variantに分かれるのか確認
frozen_medium_rules_20260603.json を修正すべきか、TIER2をsplit定義すべきか判定
```

予定出力フォルダ:

```text
Files\FX_OUTPUTS\gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only
```

予定BAT:

```text
scripts\gold_v2_runtime\bat\13D2_AUDIT_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY.bat
```

予定本体:

```text
scripts\gold_v2_runtime\audit_gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only.py
```

最初に見る予定ファイル:

```text
GOLD_V2_13D2_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY_REPORT.md
gold_v2_13d2_medium_tier2_hvt_reconciliation_summary.json
```

補助予定ファイル:

```text
gold_v2_13d2_tier2_source_rows.csv
gold_v2_13d2_tier2_final_sot_rows.csv
gold_v2_13d2_tier2_manifest_match_rows.csv
gold_v2_13d2_tier2_manifest_mismatch_rows.csv
gold_v2_13d2_tier2_feature_range_by_match_status.csv
gold_v2_13d2_tier2_variant_candidates.csv
gold_v2_13d2_tier2_reconciliation_decision_matrix.csv
gold_v2_13d2_tier2_blockers.csv
```

13D-2成功条件:

```text
TIER2_HVT mismatch 12件の特徴が説明できる
final SOT TIER2 mismatch 11件の条件領域が説明できる
manifestを修正するか、TIER2 variantsに分けるか、live不可にするかを明確化
external actionsは全てfalseのまま
```

13D-2停止条件:

```text
TIER2 source rowsに必要feature列が無い
mismatchが単一条件やvariantで説明できない
source ledgerが historical-only で live-computable conditionに落とせない
```

---

## 12. 次チャット冒頭に貼る指示文

次チャットでは以下をそのまま貼れば続行しやすい。

```text
repo: knitanr-a11y/xauusd-signal-lab

このハンドオフを読んで続きからお願いします。
対象ドキュメント:
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_13A_13D_MEDIUM_TIER2_RECONCILIATION_20260605.md

現在位置:
13Dまで完了。
CoreAはA gate未凍結でlive blocked。
CoreBはsame_count/cluster_id元クラスタリング未復元でhistorical SOT only / live blocked。
MEDIUMはarbitration replayがfinal SOT 87件と一致。ただしTIER2_HVT manifest mismatchが残っている。

次にやること:
13D2_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY

目的:
TIER2_HVTのsource 31件、final SOT 13件、manifest mismatch 12件/11件を分解し、
frozen_medium_rules_20260603.json を修正すべきか、TIER2_HVTをvariant分割すべきか、
それともlive不可として止めるべきかをaudit-onlyで判定してください。

禁止:
AI API禁止、Discord禁止、MT5禁止、live hook禁止。
近似実装禁止。SOT/source ledgerをsource of truthにしてください。
OHLCから再探索しないでください。
フォルダ名・BAT名・レポート名は 13D2 / 14A のように番号を先頭に入れてください。
```

---

## 13. 注意点

### 12Q BATに関する過去の注意

12Qのno-tabulate wrapperは作成済みだが、以前の会話で元BAT更新が409 conflictで失敗した可能性がある。

該当:

```text
scripts/gold_v2_runtime/freeze_gold_v2_final_portfolio_sot_audit_only_no_tabulate.py
commit: caaf950e2507259f06ddc7e43b5ed2b0ac560bcf
```

もし12Qで `tabulate` エラーが出たら、元BATを再確認し、no-tabulate版BATを追加/修正すること。

---

## 14. 現在の総合判断

```text
Final SOT 529 rows:
  historical SOTとして確定

CoreA:
  historical ready
  live blocked by A gate/fold4 executable mapping

CoreB:
  historical SOT allowed
  live blocked by same_count/cluster membership missing original algorithm

MEDIUM:
  historical arbitration replay OK
  live blocked by TIER2_HVT manifest mismatch + feature/asof parity + HIGH dependency

External:
  all disabled
```

次の作業は **13D-2**。
