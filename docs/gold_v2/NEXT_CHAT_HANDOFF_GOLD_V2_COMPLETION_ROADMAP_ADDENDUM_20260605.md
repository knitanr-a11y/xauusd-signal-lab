# NEXT CHAT HANDOFF ADDENDUM — GOLD V2 completion roadmap after 13D-2

作成日: 2026-06-05  
対象repo: `knitanr-a11y/xauusd-signal-lab`  
対応元ハンドオフ: `docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_13A_13D_MEDIUM_TIER2_RECONCILIATION_20260605.md`  
目的: 13D-2以降の「どこを完成形とするか」を明確化する。

---

## 1. なぜこの追記が必要か

既存ハンドオフには、13A〜13Dの結果、13D-2の入力・期待件数・停止条件は入っている。  
ただし、13D-2以降に最終的にどこへ向かうか、つまり「完成形」までのロードマップが薄かった。

この追記では、13D-2後の工程、13系の完了条件、14系のdry-run完成形、外部送信/発注をいつまで禁止するかを固定する。

---

## 2. 当面の完成形

当面の完成形は、以下。

```text
GOLD_V2_LIVE_DRY_RUN_EVALUATOR_READY_NO_EXTERNAL_ACTIONS
```

これは、Discord送信やMT5発注を開始する状態ではない。  
まずは、SOTを壊さず、liveで計算可能なcomponentだけを使う **dry-run evaluator** を完成させる。

完成条件:

```text
1. final SOT 529件は historical reference として保持
2. live eligible components と historical-only components が明確に分離されている
3. live eligible componentsだけで最新足から候補を出せる
4. 候補出力はCSV/JSON/Markdown previewのみ
5. Discord/MT5/AI/live hookはOFF
6. 近似実装はゼロ
7. 使用したfeature/asof timingがドキュメント化されている
8. どのcomponentがliveから除外されたか理由付きで残っている
```

---

## 3. 13系の最終ゴール

13系の最終ゴールは以下。

```text
GOLD_V2_COMPONENT_LIVE_ELIGIBILITY_MATRIX_READY_AUDIT_ONLY
```

意味:

```text
CoreA / CoreB / MEDIUM の各sourceについて、
1. historical SOTとして使えるもの
2. live evaluatorに入れられるもの
3. historical-onlyとして残すもの
4. 近似禁止で停止すべきもの
を明確に分ける。
```

13系の完了時点でも、以下はまだ false のまま。

```text
final_signal_allowed = false
discord_send_allowed = false
mt5_order_allowed = false
ai_api_allowed = false
live_hook_allowed = false
```

---

## 4. 14系に進める条件

14系に進む条件は、以下のような live eligibility matrix を作れること。

```text
Files\FX_OUTPUTS\gold_v2_13f_component_live_eligibility_matrix_audit_only\GOLD_V2_13F_COMPONENT_LIVE_ELIGIBILITY_MATRIX_AUDIT_ONLY_REPORT.md
Files\FX_OUTPUTS\gold_v2_13f_component_live_eligibility_matrix_audit_only\gold_v2_13f_component_live_eligibility_matrix_summary.json
Files\FX_OUTPUTS\gold_v2_13f_component_live_eligibility_matrix_audit_only\gold_v2_13f_component_live_eligibility_matrix.csv
```

matrixには最低限以下を入れる。

```text
component
historical_sot_allowed
live_evaluator_allowed
live_evaluator_status
blocking_reason
required_fields
required_feature_parity_status
source_ledger_reference
historical_rows
final_sot_rows
approximation_allowed=false
external_action_allowed=false
```

---

## 5. 13D-2以降の工程順

### 5.1 13D-2 — TIER2_HVT reconciliation

```text
13D2_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY
```

目的:

```text
TIER2_HVT source 31件 / final SOT 13件 / manifest mismatch 12件・11件を分解する。
```

出力で決めること:

```text
TIER2_HVTを単一修正版で説明できるか
複数variantに分割すべきか
historical-onlyで止めるべきか
```

### 5.2 13D-3 — TIER2_HVT freeze / split / block

13D-2の結果で3分岐する。

A. 単一修正版で説明できる場合:

```text
13D3_FREEZE_MEDIUM_TIER2_HVT_RECONCILED_RULE_AUDIT_ONLY
```

B. 複数variantが必要な場合:

```text
13D3_SPLIT_MEDIUM_TIER2_HVT_VARIANTS_AUDIT_ONLY
```

C. live条件化できない場合:

```text
13D3_MEDIUM_TIER2_HVT_HISTORICAL_ONLY_BLOCK_AUDIT_ONLY
```

この時点でも、まだlive signalは出さない。

### 5.3 13E — MEDIUM feature/asof parity

```text
13E_MEDIUM_FEATURE_ASOF_PARITY_PREFLIGHT_AUDIT_ONLY
```

目的:

```text
RANGE96_REFINED
VOL_TRMEAN32_REFINED
TIER2_HVTまたはTIER2分割variant
```

について、live evaluatorに必要なfeatureがsource ledgerと同じ意味・同じ時刻で計算できるか確認する。

最低限見るfeature:

```text
range96
trend_eff96
ret96
tr_mean_32
regime
top_direction
entry_time / top_entry_time
M15 close基準かどうか
```

13E成功条件:

```text
live feature/asof parityが証明できたcomponentだけ live_evaluator_allowed=true candidate にできる。
証明できないcomponentは historical-only にする。
```

### 5.4 13F — component live eligibility matrix

```text
13F_BUILD_COMPONENT_LIVE_ELIGIBILITY_MATRIX_AUDIT_ONLY
```

目的:

```text
CoreA / CoreB / MEDIUM の全componentについて、liveに入れる・入れないを最終整理する。
```

現時点の想定:

```text
CoreA:
  A gate未凍結のため live blocked の可能性が高い
  B/Cだけ部分liveにする場合も CoreA_REJECT順序が必要

CoreB:
  historical SOT allowed
  original clustering algorithm未復元のため live blocked

MEDIUM:
  RANGE96_REFINED と VOL_TRMEAN32_REFINED は有望
  TIER2_HVT は13D-2/13D-3次第
```

13Fの出力例:

```text
Files\FX_OUTPUTS\gold_v2_13f_component_live_eligibility_matrix_audit_only
GOLD_V2_13F_COMPONENT_LIVE_ELIGIBILITY_MATRIX_AUDIT_ONLY_REPORT.md
gold_v2_13f_component_live_eligibility_matrix_summary.json
gold_v2_13f_component_live_eligibility_matrix.csv
gold_v2_13f_historical_only_components.csv
gold_v2_13f_live_candidate_components.csv
```

### 5.5 13G — combined dry-run evaluator design audit

```text
13G_COMBINED_DRY_RUN_EVALUATOR_DESIGN_AUDIT_ONLY
```

目的:

```text
13Fでlive_evaluator_allowed=trueになったcomponentだけを使って、
今後のdry-run live evaluator設計を確定する。
```

注意:

```text
historical-only componentはlive signalに使わない。
ただしreport上の過去SOT成績には残す。
```

13Gで決めること:

```text
入力OHLC/feature snapshot
M15/M5 asof timing
component priority
HIGH vs MEDIUM arbitration
出力CSV形式
通知文面preview形式
external actions disabled policy
```

---

## 6. 14系の完成形ロードマップ

14系は、13系で live eligible とされたcomponentだけを使う。

### 6.1 14A — runtime dry-run evaluator

```text
14A_RUNTIME_LIVE_CANDIDATE_EVALUATOR_DRY_RUN_ONLY
```

完成形:

```text
最新OHLC/featureからlive candidateを計算する。
ただし発注・通知はしない。
出力CSV/JSON/Markdownだけ作る。
```

想定出力:

```text
Files\FX_OUTPUTS\gold_v2_14a_runtime_live_candidate_evaluator_dry_run_only
GOLD_V2_14A_RUNTIME_LIVE_CANDIDATE_EVALUATOR_DRY_RUN_ONLY_REPORT.md
gold_v2_14a_runtime_live_candidate_summary.json
gold_v2_14a_runtime_live_candidate_rows.csv
```

### 6.2 14B — notification preview only

```text
14B_NOTIFICATION_PREVIEW_DRY_RUN_ONLY
```

完成形:

```text
Discordに送る予定の文面をpreviewとして生成する。
実送信はしない。
```

### 6.3 14C — dry-run parity / safety gate

```text
14C_DRY_RUN_PARITY_AND_SAFETY_GATE_AUDIT_ONLY
```

完成形:

```text
live candidate evaluatorの出力が、過去SOT/eligible componentsと矛盾しないか確認する。
全てのsafety flagがfalseのままか確認する。
```

想定出力:

```text
Files\FX_OUTPUTS\gold_v2_14c_dry_run_parity_and_safety_gate_audit_only\GOLD_V2_14C_DRY_RUN_PARITY_AND_SAFETY_GATE_AUDIT_ONLY_REPORT.md
Files\FX_OUTPUTS\gold_v2_14c_dry_run_parity_and_safety_gate_audit_only\gold_v2_14c_dry_run_parity_and_safety_gate_summary.json
Files\FX_OUTPUTS\gold_v2_14c_dry_run_parity_and_safety_gate_audit_only\gold_v2_14c_live_candidate_rows.csv
Files\FX_OUTPUTS\gold_v2_14c_dry_run_parity_and_safety_gate_audit_only\gold_v2_14c_notification_preview.md
Files\FX_OUTPUTS\gold_v2_14c_dry_run_parity_and_safety_gate_audit_only\gold_v2_14c_safety_flags.json
```

### 6.4 14D以降 — external actionは明示許可後のみ

Discord実送信やMT5接続は、14A〜14Cが通った後に、ユーザーが明示的に許可した場合だけ。

```text
Discord送信 = まだ禁止
MT5発注 = まだ禁止
AI API = まだ禁止
```

---

## 7. 完成形ではないもの

以下は完成形ではない。

```text
historical top_ledgers の cluster_id/same_count をそのままlive triggerに使う
CoreB same_countを固定windowやconnected componentで近似する
TIER2_HVT mismatchを無視してmanifestを通す
CoreA A gateを is_A flag だけでlive実装する
source rowsにないfeatureをOHLCから再探索して採用する
Discord/MT5/AIを先にONにする
```

---

## 8. 次チャットでの推奨実行順（完成形まで）

```text
13D2  TIER2_HVT source definition reconciliation
13D3  TIER2_HVT freeze / split / historical-only block
13E   MEDIUM feature/asof parity preflight
13F   component live eligibility matrix
13G   combined dry-run evaluator design
14A   runtime live candidate evaluator dry-run only
14B   notification preview dry-run only
14C   dry-run parity and safety gate
```

ここまで通って初めて、外部送信・発注の議論に進める。  
それまでは、**全てaudit-only / dry-run-only**。
