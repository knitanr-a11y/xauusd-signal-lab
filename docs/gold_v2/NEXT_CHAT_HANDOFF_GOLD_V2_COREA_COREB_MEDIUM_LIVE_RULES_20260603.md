# NEXT CHAT HANDOFF - GOLD V2 CoreA / CoreB / MEDIUM live-rule evaluation

Date: 2026-06-03  
Repo: `knitanr-a11y/xauusd-signal-lab`

このドキュメントは、新しいチャットで作業を継続するための引き継ぎです。  
GOLD V2で、旧GOLD/DISC8のHTF open-time不整合を避けたうえで、CoreA / CoreB / MEDIUMを探索・検証・採用候補化し、audit-only live導線まで進めた経緯と、次にやるべき作業をまとめます。

---

## 0. 最重要ルール

以下は絶対に守ること。

1. **旧GOLD / DISC8 の実装・探索結果を source of truth に戻さない。**
2. **HTFはopen timeではなく、必ず `open_time + duration <= M15 eval_time` で確定済み足だけを使う。**
3. **探索済み結果を近似再実装しない。**
4. **CoreA/CoreBのlive再判定は、凍結済みルール定義をsource of truthにして行う。**
5. **Discord通知、MT5発注、AI API、live hookは、別途明示許可が出るまで全てOFF。**
6. **NO_SIGNALではDiscord通知しない。通知文面も空にする。**
7. **シグナルなし理由は監査ファイルには残してよいが、Discordに送らない。**
8. **部分的・推測的・簡略実装は禁止。必ずフル実装で、入出力・成功条件・停止条件を明示する。**

---

## 1. 背景: なぜGOLD V2を作ったか

旧GOLD/DISC8系は、HTF open-timeの扱いにより、H1/H4/D1の未確定情報がM15評価時点へ混入する疑いがあった。  
そのため、旧探索・旧AI評価導線は隔離し、GOLD V2として以下を前提に再構築した。

- M15評価時刻に対して、H1/H4/D1は確定済みのみ使用。
- dispatch_readyや通知済み結果をsource of truthにしない。
- ローソク足から再評価する場合も、探索時の定義・候補宇宙・ルール条件とズレないこと。
- AI評価はまだ接続しない。
- Discord/MT5/live hookもまだ接続しない。

---

## 2. 探索から本採用候補までの流れ

### 2.1 CoreAの発見

CoreAは、GOLD V2で最初に本命になった高信頼コア。

採用形:

```text
CoreA = fold4_rules + ABC entry gate + A_CAP5_BC_CAP3 sizing
```

意味:

- `fold4_rules` をベースにする。
- ABC entry gateでA/B/Cを分類する。
- AはCAP5。
- B/CはCAP3。
- priorityは `HIGH_A`。
- 初期ロット候補は `1.0`。

ABCの大枠:

```text
A:
  10日 lookback
  tail_hard
  top5
  all consensus
  stack許可のみKEEP
  それ以外REJECT

B:
  CoreA rejected
  AND regime == MID_MIXED
  AND trend_eff96 >= 0.633155
  AND RR >= 1.5

C:
  range96 >= 100.43
  AND range96 <= 117.86
```

2025/2026で確認されたCoreA実績:

| Dataset | Count | WR | PF | TotalR | Worst | MaxDD | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2025_fold4 | 200 | 65.50% | 2.38 | +230.24R | -5R | 16.20R | 5 |
| 2026_WF | 125 | 73.60% | 3.80 | +193.5R | -5R | 7R | 2 |

CoreAは採用候補の中心で、現在のlive導線では `HIGH_A_CoreA_fold4_ABC_CAP5` として扱う。

---

### 2.2 CoreBの発見

CoreBは、CoreAとは別のBUY専用第二Core候補。

採用形:

```text
CoreB = RR125_BUY_CONFLUENCE
```

定義:

```text
source_rules = BUY rules originally selected at RR1.0
TP = 1.25 * SL
same_count >= 15
sizing = CAP3
priority = HIGH_B
initial lot = 1.0
```

重要: RR1.25は既存selected-rules universeにそのまま存在したわけではなく、RR1.0由来BUYルールのエントリー条件とSL幅を維持し、TPだけ `1.25 * SL` に変えて再評価したもの。

Standalone実績:

| Dataset | Count | WR | PF | TotalR | Worst | MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| 2025 | 104 | 72.12% | 3.44 | +143.02R | -3R | 7.5R |
| 2026 | 21 | 80.95% | 5.15 | +40.50R | -3R | 6.0R |

CoreA + RR1.25 CoreB:

| Dataset | Count | WR | PF | TotalR |
|---|---:|---:|---:|---:|
| 2025 | 297 | 67.00% | 2.56 | +351.51R |
| 2026 | 138 | 74.64% | 4.02 | +226.50R |

CoreA BUYとCoreB BUYが同じentry_timeで重なる場合は、初期案としてCoreB側の追加露出を `+0.5` とし、合計1.5相当にする。

CoreA SELLとCoreB BUYが同時刻で衝突する場合は、CoreA優先でCoreBをskipする。これは別途conflict auditが承認されるまで変更しない。

---

### 2.3 MEDIUM候補

MEDIUMはCoreA/CoreBより下位の補助候補。  
HIGH_A / HIGH_B が優先で、MEDIUMはそれらと同時刻に重なる場合はskipまたはarbitration対象。

採用候補:

```text
MEDIUM:
  RANGE96_REFINED
  VOL_TRMEAN32_REFINED
  TIER2_HVT

WATCH:
  ORIGIN010_REFINED
```

MEDIUMの初期ロット候補は `0.5`。

#### RANGE96_REFINED

```text
range96 >= 129.6835
AND trend_eff96 <= 0.355591
AND top_direction == SELL
CAP3
```

#### VOL_TRMEAN32_REFINED

```text
tr_mean_32 >= 10.867578
AND ret96 <= -2.725
AND range96 >= 176.453
CAP3
```

#### TIER2_HVT

```text
trend_eff96 <= 0.4
AND ret96 <= -25.0
AND tr_mean_32 >= 10.867578
CAP3
```

注意: MEDIUMは特徴条件だけで即シグナル化してはいけない。CoreA/CoreBのarbitration後に最終判断する。

---

## 3. 現在の採用ポリシー

最終的な現時点の構成:

```text
HIGH_A:
  CoreA = fold4_rules + ABC + A_CAP5_BC_CAP3

HIGH_B:
  CoreB = RR125_BUY_CONFLUENCE

HIGH_CONFLUENCE:
  CoreA BUY + CoreB BUY same entry_time
  initial extra CoreB exposure = 0.5

MEDIUM:
  RANGE96_REFINED
  VOL_TRMEAN32_REFINED
  TIER2_HVT

WATCH:
  ORIGIN010_REFINED
```

全体成績:

| Dataset | 構成 | Count | WR | PF | TotalR | Worst | MaxDD |
|---|---|---:|---:|---:|---:|---:|---:|
| 2025 | CoreA + CoreB + MEDIUM, 重複0.5 | 346 | 69.08% | 2.84 | +439.51R | -5R | 19.2R |
| 2026 | CoreA + CoreB + MEDIUM, 重複0.5 | 183 | 72.13% | 3.65 | +248.75R | -5R | 7.0R |

---

## 4. 実装済みruntime/audit導線

### 4.1 03 - CoreA/CoreB/MEDIUM監査

```text
scripts/gold_v2_runtime/evaluate_gold_v2_coreA_coreB_medium_audit_only.py
scripts/gold_v2_runtime/bat/03_RUN_COREA_COREB_MEDIUM_AUDIT_ONLY.bat
```

役割:

- 探索済み出力CSVからCoreA/CoreB/MEDIUM portfolioを再集計。
- demo/liveではなくaudit-only。

---

### 4.2 04 - policy preflight

```text
scripts/gold_v2_runtime/bat/04_RUN_COREA_COREB_MEDIUM_POLICY_PREFLIGHT.bat
```

役割:

- 必要CSVが存在するか。
- policy configが安全設定になっているか。
- `ai_api_enabled=false` / `discord_enabled=false` / `mt5_order_enabled=false` / `live_hook_enabled=false` を確認。

---

### 4.3 05 - runtime signal candidates export

```text
scripts/gold_v2_runtime/export_gold_v2_runtime_signal_candidates_audit_only.py
scripts/gold_v2_runtime/bat/05_EXPORT_RUNTIME_SIGNAL_CANDIDATES_AUDIT_ONLY.bat
```

出力:

```text
Files/FX_OUTPUTS/gold_v2_runtime_signal_candidates_audit_only
```

主なファイル:

```text
gold_v2_runtime_signal_candidates.csv
gold_v2_runtime_signal_candidates.jsonl
gold_v2_runtime_signal_candidates_latest.json
gold_v2_runtime_signal_candidates_summary.csv
gold_v2_runtime_signal_candidates_summary.json
GOLD_V2_RUNTIME_SIGNAL_CANDIDATES_AUDIT_ONLY_REPORT.md
```

確認済み:

```text
529件
2025: 346件
2026: 183件
HIGH_A: 317件
HIGH_B: 117件
HIGH_CONFLUENCE: 8件
MEDIUM: 87件
```

---

### 4.4 06 - notification preview

```text
scripts/gold_v2_runtime/render_gold_v2_notification_preview_audit_only.py
scripts/gold_v2_runtime/bat/06_RENDER_NOTIFICATION_PREVIEW_AUDIT_ONLY.bat
```

仕様:

- デフォルトdatasetは `2026` のみ。
- 2025/2026両方見たい場合は `--datasets 2025,2026`。
- 実送信はしない。

通知例:

```text
【GOLD】🔴 SELL｜HIGH_A / CoreA本命
━━━━━━━━━━━━━━━━━━━━
時刻: 2026-06-02 01:15:00
エントリー: 4481.48
TP: 4466.48（-15.00）
SL: 4496.48（+15.00）
種別: CoreA_fold4_ABC_CAP5
根拠: fold4_rules + ABCゲート + CAP5/CAP3 sizing
ロット候補: 1.00
検証R: +2.00R

状態: AUDIT ONLY（外部送信なし）
メモ: CoreA本命。単独ロット候補1.0。
```

---

### 4.5 07 - live audit packet

```text
scripts/gold_v2_runtime/build_gold_v2_live_audit_packet_audit_only.py
scripts/gold_v2_runtime/bat/07_BUILD_LIVE_AUDIT_PACKET_AUDIT_ONLY.bat
```

仕様:

- デフォルトdatasetは `2026`。
- latest候補、summary、通知プレビュー、安全ゲートを1つのpacketにまとめる。
- 外部送信/発注/AI/live hookは全OFF。

確認済み状態:

```text
status = AUDIT_ONLY_LIVE_PACKET
datasets = ["2026"]
safety_gate = BLOCK_EXTERNAL_ACTIONS
discord_send_allowed = false
mt5_order_allowed = false
ai_api_allowed = false
live_hook_allowed = false
```

---

### 4.6 08 - latest candle candidate bridge

```text
scripts/gold_v2_runtime/build_gold_v2_latest_candle_candidate_audit_only.py
scripts/gold_v2_runtime/bat/08_BUILD_LATEST_CANDLE_CANDIDATE_AUDIT_ONLY.bat
```

役割:

- 最新M15足の時刻を取得。
- 監査済みruntime candidates CSVに同時刻の候補があるか確認。
- 候補があればaudit-only previewを出す。
- 候補が無ければ `NO_SIGNAL`。

注意:

- これはローソク足からCoreA/CoreBを再判定する本体ではない。
- 監査済み候補CSVとの同時刻照合ブリッジ。

確認済み例:

```text
status = NO_SIGNAL
eval_time = 2026-06-03 15:15:00
```

---

### 4.7 09 - latest feature snapshot

```text
scripts/gold_v2_runtime/build_gold_v2_latest_feature_snapshot_audit_only.py
scripts/gold_v2_runtime/bat/09_BUILD_LATEST_FEATURE_SNAPSHOT_AUDIT_ONLY.bat
```

役割:

- 最新M15足の特徴量を計算。
- MEDIUM系の特徴条件ヒット状況を確認。
- ここではまだ `FEATURE_PROBE_ONLY`。

計算する主な特徴:

```text
ret96
range96
trend_eff96
tr_mean_32
ret32
range32
direction_bar
```

確認済み例:

```text
2026-06-03 15:45:00
ret96 = -67.15
range96 = 95.15
trend_eff96 = 0.7057
tr_mean_32 = 10.2263
MEDIUM all false
```

---

### 4.8 10 - live rule evaluation audit gate

```text
scripts/gold_v2_runtime/evaluate_gold_v2_live_rules_audit_only.py
scripts/gold_v2_runtime/bat/10_EVALUATE_LIVE_RULES_AUDIT_ONLY.bat
```

役割:

- latest featureを使い、live rule evaluation gateとして実行。
- CoreA/CoreBの凍結ルールsourceが無い場合は `RULE_SOURCE_MISSING` で停止。
- 凍結sourceがあっても evaluator mapping 未実装なら `RULE_SOURCE_PRESENT_BUT_EVALUATOR_NOT_IMPLEMENTED` で停止。
- MEDIUM特徴条件は評価するが、CoreA/CoreB arbitration未接続なら最終signalにしない。

重要仕様:

```text
NO_SIGNAL時:
  notification_should_send = false
  notification_preview_text = ""
  no_signal_discord_policy = DO_NOT_NOTIFY_ON_NO_SIGNAL
```

つまり、シグナル無しではDiscord通知しない。

確認済み例:

```text
final_signal_status = NO_SIGNAL
notification_should_send = false
notification_preview_text = ""
mt5_order_allowed = false
```

---

### 4.9 11 - frozen rule source generator

```text
scripts/gold_v2_runtime/freeze_gold_v2_rule_sources_audit_only.py
scripts/gold_v2_runtime/bat/11_FREEZE_RULE_SOURCES_AUDIT_ONLY.bat
```

役割:

- ユーザー環境の探索済みCSVを読み、CoreA/CoreB/MEDIUMの凍結source manifest JSONを生成。
- これはlive evaluatorそのものではない。
- ファイル存在、sha256、行数、列、採用条件、近似再実装禁止を固定する。

生成されるconfig:

```text
configs/gold_v2/frozen_coreA_fold4_ABC_CAP5_rules_20260603.json
configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json
configs/gold_v2/frozen_medium_rules_20260603.json
```

監査コピー:

```text
Files/FX_OUTPUTS/gold_v2_frozen_rule_sources_audit_only
```

確認済み:

```text
CoreA status = FROZEN_RULE_SOURCE_READY
CoreB status = FROZEN_RULE_SOURCE_READY
MEDIUM status = FROZEN_RULE_SOURCE_READY
```

---

## 5. 直近の状態

直近でユーザーが10番を再実行したログ:

```text
NO_SIGNAL: Discord notification preview is intentionally empty.

[OK] GOLD V2 live rule evaluation audit gate completed.
Output is under Files\FX_OUTPUTS\gold_v2_live_rule_evaluation_audit_only by default.
```

このログは正しい。

理由:

- シグナルが無い。
- NO_SIGNALなのでDiscord通知文面は空。
- 外部送信なし。

次に10番の出力ファイルを確認すべき:

```text
gold_v2_live_rule_evaluation_packet.json
GOLD_V2_LIVE_RULE_EVALUATION_AUDIT_ONLY_REPORT.md
gold_v2_live_rule_core_eval.csv
gold_v2_live_rule_medium_eval.csv
```

確認したいポイント:

```text
CoreA/CoreBが RULE_SOURCE_MISSING から脱出しているか。
期待:
  RULE_SOURCE_PRESENT_BUT_EVALUATOR_NOT_IMPLEMENTED
```

---

## 6. レポートが見当たらない件

`GOLD_V2_FROZEN_RULE_SOURCES_AUDIT_ONLY_REPORT.md` が見当たらないとのこと。

想定パス:

```text
Files/FX_OUTPUTS/gold_v2_frozen_rule_sources_audit_only/GOLD_V2_FROZEN_RULE_SOURCES_AUDIT_ONLY_REPORT.md
```

`configs/gold_v2` にはJSONだけが出る。Markdownレポートは `Files/FX_OUTPUTS` 側に出す設計。  
ただし、JSON3本が生成済みで `FROZEN_RULE_SOURCE_READY` なら、現時点では致命的ではない。

---

## 7. 次にやるべきこと

### Step 1: 10番の再出力確認

11番で凍結JSONが作られた後に、10番を再実行した。

次チャットではまず以下のファイルを確認する:

```text
gold_v2_live_rule_evaluation_packet.json
GOLD_V2_LIVE_RULE_EVALUATION_AUDIT_ONLY_REPORT.md
gold_v2_live_rule_core_eval.csv
gold_v2_live_rule_medium_eval.csv
```

確認項目:

```text
CoreA status
CoreB status
final_signal_status
notification_preview_text
notification_should_send
```

期待:

```text
CoreA/CoreB:
  RULE_SOURCE_PRESENT_BUT_EVALUATOR_NOT_IMPLEMENTED

NO_SIGNALの場合:
  notification_preview_text = ""
  notification_should_send = false
```

---

### Step 2: 12番 evaluator mapping を実装する

次に作るべきスクリプト:

```text
scripts/gold_v2_runtime/map_gold_v2_frozen_rules_to_live_evaluator_audit_only.py
scripts/gold_v2_runtime/bat/12_MAP_FROZEN_RULES_TO_LIVE_EVALUATOR_AUDIT_ONLY.bat
```

目的:

```text
frozen_coreA / frozen_coreB / frozen_medium
  ↓
実際にlive評価可能な条件へmapping
  ↓
近似ではなく、manifestのsource CSV列と明示条件を使う
  ↓
10番の evaluator mapping に接続
```

ここで絶対にしてはいけないこと:

```text
- historical ledgerのentry_time一致だけでlive signalにする
- top_entry_timeやcluster ledgerをそのまま未来予測として使う
- fold4_rulesを推測で再現する
- CoreB RR125 BUY条件を曖昧に再実装する
```

まず作るべき中間成果物:

```text
configs/gold_v2/live_evaluator_mapping_coreA_20260603.json
configs/gold_v2/live_evaluator_mapping_coreB_20260603.json
configs/gold_v2/live_evaluator_mapping_medium_20260603.json
```

mappingの中身:

- 使用するsourceファイルのsha256。
- 使用する列名。
- ルール条件式。
- 必須特徴量。
- 欠損時の停止条件。
- evaluatorが未対応の条件。
- 近似禁止フラグ。

---

### Step 3: 13番 live evaluator 実装

12番でmappingができたら、13番で10番に実評価を接続する。

候補名:

```text
scripts/gold_v2_runtime/evaluate_gold_v2_live_rules_with_mapping_audit_only.py
scripts/gold_v2_runtime/bat/13_EVALUATE_LIVE_RULES_WITH_MAPPING_AUDIT_ONLY.bat
```

目的:

```text
最新M15/H1/H4/D1/M1/M5
  ↓
HTF確定済み制約を守って特徴量生成
  ↓
CoreA/CoreB/MEDIUM mappingで条件判定
  ↓
arbitration
  ↓
SIGNAL or NO_SIGNAL
```

外部送信はまだしない。

SIGNALの場合だけ:

```text
notification_preview_text を作成
notification_should_send = false  # audit-onlyなのでまだfalse
```

NO_SIGNALの場合:

```text
notification_preview_text = ""
notification_should_send = false
```

---

### Step 4: demo前preflight

live evaluatorが安定したら、次にpreflightを追加。

候補:

```text
scripts/gold_v2_runtime/preflight_gold_v2_live_evaluator_audit_only.py
scripts/gold_v2_runtime/bat/14_PREFLIGHT_LIVE_EVALUATOR_AUDIT_ONLY.bat
```

確認項目:

```text
- HTF確定済み制約OK
- M15最新足あり
- M1/M5判定用データあり
- mapping source sha一致
- missing featureなし
- Discord false
- MT5 false
- AI false
- live_hook false
- NO_SIGNAL通知禁止
```

---

### Step 5: Discord/MT5はまだ後

現時点でまだやらないこと:

```text
Discord実送信
MT5発注
AI API再評価
live hook接続
```

これらはlive evaluatorとpreflightが完成し、ユーザーが明示許可してから別フェーズで行う。

---

## 8. 次チャットで最初に貼る指示文

新チャットでは、以下を貼るとよい。

```text
repo: knitanr-a11y/xauusd-signal-lab

まず docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_COREA_COREB_MEDIUM_LIVE_RULES_20260603.md を読んでください。

GOLD V2は、CoreA/CoreB/MEDIUM探索からaudit-only live導線まで進んでいます。
旧GOLD/DISC8はHTF open-time不整合疑いで隔離済みです。
近似再実装は禁止です。
Discord通知・MT5発注・AI API・live hookは明示許可までOFFです。
NO_SIGNAL時はDiscord通知しません。

現状:
- 03〜11まで実装済み。
- 11番で frozen_coreA / frozen_coreB / frozen_medium のJSONは生成済みで、FROZEN_RULE_SOURCE_READYです。
- 10番はlive rule evaluation audit gateです。
- 次は10番の出力を確認し、CoreA/CoreBが RULE_SOURCE_MISSING から RULE_SOURCE_PRESENT_BUT_EVALUATOR_NOT_IMPLEMENTED に進んだか確認してください。
- その後、12番として frozen rule sourceをlive evaluator mappingへ落とす作業に進めてください。

やること:
1. 直近の10番出力を確認。
2. CoreA/CoreB frozen JSONとpolicy JSONを読み、source of truthを確認。
3. 12_MAP_FROZEN_RULES_TO_LIVE_EVALUATOR_AUDIT_ONLY を設計・実装。
4. 近似再実装せず、mapping不能な条件は明示的にUNMAPPEDとして止める。
5. NO_SIGNAL通知は禁止のまま維持。

実装前に必ず仕様書を書き、入力CSV/JSON、出力、成功条件、停止条件、外部送信の有無を明記してください。
```

---

## 9. 現在の到達点の結論

GOLD V2は、探索・比較・採用判断・audit-only候補出力・通知文面プレビュー・live packet・latest candle bridge・feature snapshot・live rule audit gate・frozen source generationまで完了。

まだ未完了なのはここ:

```text
凍結source manifest
  ↓
明示的 live evaluator mapping
  ↓
実際のCoreA/CoreB/MEDIUM live再判定
```

ここを次チャットで進める。

