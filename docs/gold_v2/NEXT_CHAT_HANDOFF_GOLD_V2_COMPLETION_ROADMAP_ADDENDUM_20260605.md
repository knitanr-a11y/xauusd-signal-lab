# NEXT CHAT HANDOFF ADDENDUM — GOLD V2 true completion target: Discord + MT5 autotrading

作成日: 2026-06-05  
対象repo: `knitanr-a11y/xauusd-signal-lab`  
対応元ハンドオフ: `docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_13A_13D_MEDIUM_TIER2_RECONCILIATION_20260605.md`  
重要修正: **dry-run evaluator は中間ゲートであり、完成形ではない。完成形は Discord通知 + MT5自動売買。**

---

## 1. この追記の目的

前回の完成形ロードマップでは、当面の中間ゲートである

```text
GOLD_V2_LIVE_DRY_RUN_EVALUATOR_READY_NO_EXTERNAL_ACTIONS
```

を「完成形」のように書いてしまっていた。これは不十分。

正しい最終完成形は以下。

```text
GOLD_V2_DISCORD_NOTIFIED_MT5_GUARDED_AUTOTRADE_READY
```

ただし、ここへ進むには段階ゲートが必要。  
いきなりDiscord実送信やMT5発注をONにしてはいけない。

---

## 2. 真の完成形

真の完成形は、以下の全てを満たす状態。

```text
1. live evaluator が最新足から売買候補を生成する
2. 条件を満たした候補を Discord に実通知する
3. 許可された候補を MT5 に自動発注する
4. MT5上の建玉・約定・決済を追跡する
5. 発注前後の特徴量・判定理由・通知内容・注文結果をledger化する
6. 約定後の勝敗・SL/TP/手動決済/ポジション不一致を監査できる
7. 異常時は自動売買を止める安全装置がある
8. 近似実装なし。live対象componentはSOT/source定義から説明できる
```

完成形の状態名:

```text
GOLD_V2_DISCORD_NOTIFIED_MT5_GUARDED_AUTOTRADE_READY
```

---

## 3. dry-run の位置づけ

dry-run は完成形ではなく、完成形に進むための中間ゲート。

```text
dry-run evaluator:
  Discord送信なし
  MT5発注なし
  AI APIなし
  live hookなし
  CSV/JSON/Markdown previewのみ
```

dry-runで確認すること:

```text
1. live対象componentだけで候補が出る
2. historical-only componentをlive signalに混ぜていない
3. feature/asof timingが正しい
4. arbitrationが正しい
5. 通知文面previewが正しい
6. 発注予定パラメータpreviewが正しい
7. safety flagsが全部falseのまま
```

---

## 4. 完成までの全体ロードマップ

### Phase 13 — Source-to-live eligibility

目的:

```text
CoreA / CoreB / MEDIUM のsourceを、liveに使えるかどうか分類する。
```

現在位置:

```text
13D完了
次は 13D2_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY
```

13系完了条件:

```text
1. CoreA / CoreB / MEDIUM の historical SOT allowed / live allowed / blocked が整理されている
2. liveに使えないcomponentをhistorical-onlyとして明示している
3. liveに使うcomponentはfeature/asof parityの監査対象になっている
4. 近似実装が混ざっていない
```

13系の最終出力:

```text
Files\FX_OUTPUTS\gold_v2_13f_component_live_eligibility_matrix_audit_only
GOLD_V2_13F_COMPONENT_LIVE_ELIGIBILITY_MATRIX_AUDIT_ONLY_REPORT.md
gold_v2_13f_component_live_eligibility_matrix_summary.json
gold_v2_13f_component_live_eligibility_matrix.csv
```

13系が終わっても、まだDiscord/MT5はOFF。

---

### Phase 14 — Runtime dry-run / notification preview / order preview

目的:

```text
live eligible componentsだけで、実運用形式の候補・通知・注文previewを作る。
```

14A:

```text
14A_RUNTIME_LIVE_CANDIDATE_EVALUATOR_DRY_RUN_ONLY
```

目的:

```text
最新OHLC/featureからlive candidateを生成する。
```

14B:

```text
14B_DISCORD_NOTIFICATION_PREVIEW_DRY_RUN_ONLY
```

目的:

```text
Discordに実送信する前の通知文面previewを作る。
```

14C:

```text
14C_MT5_ORDER_REQUEST_PREVIEW_DRY_RUN_ONLY
```

目的:

```text
MT5に送る予定のorder requestをpreviewとして作る。
実発注はしない。
```

確認項目:

```text
symbol
direction
lot
entry type
SL
TP
magic number
comment
deviation
fill policy
max spread
max concurrent positions
cooldown
duplicate guard
```

14D:

```text
14D_DRY_RUN_PARITY_AND_SAFETY_GATE_AUDIT_ONLY
```

目的:

```text
14A〜14Cのcandidate / notification / order previewが矛盾していないか確認する。
```

14系完了条件:

```text
1. candidate rowsが説明可能
2. notification previewが正しい
3. MT5 order request previewが正しい
4. duplicate / cooldown / position guard がpreview上で効いている
5. external actionsはまだfalse
```

---

### Phase 15 — External integration staging

Phase 15は、ユーザーの明示許可後のみ進める。

15A:

```text
15A_DISCORD_SEND_SANDBOX_OR_TEST_CHANNEL_AUDIT_ONLY
```

目的:

```text
Discord実送信をテストチャンネルまたは明示指定チャンネルで確認する。
MT5発注はまだOFF。
```

15B:

```text
15B_MT5_CONNECTION_AND_ACCOUNT_STATE_AUDIT_ONLY
```

目的:

```text
MT5接続、口座情報、symbol仕様、最小lot、digits、point、spread、trade_allowedを読む。
発注はまだしない。
```

15C:

```text
15C_MT5_ORDER_SEND_DEMO_GUARDED_AUTOTRADE_TEST
```

目的:

```text
デモ口座で、最小lotまたは指定lotの guarded auto order を実行する。
```

必須安全装置:

```text
demo_only または user_confirmed_live = true がない限り発注禁止
max_lot
max_positions
max_daily_trades
max_daily_loss
cooldown
duplicate signal guard
symbol whitelist
magic number
position match guard
emergency stop file
dry_run override
```

15D:

```text
15D_MT5_POSITION_MONITOR_AND_CLOSE_AUDIT
```

目的:

```text
MT5上の建玉を監視し、entry / SL / TP / close / manual close / no match をledger化する。
```

15E:

```text
15E_DISCORD_TRADE_LIFECYCLE_NOTIFICATION
```

目的:

```text
entry通知、約定通知、決済通知、勝敗通知をDiscordへ送る。
```

15系完了条件:

```text
1. Discord実通知が安定している
2. MT5接続・発注・建玉監視が安定している
3. entryからcloseまでledgerが欠損しない
4. manual close / no position match / partial close などを誤判定しない
5. emergency stopが機能する
```

---

### Phase 16 — Production guarded autotrading

Phase 16は、デモ検証後にユーザーが明示許可した場合のみ。

16A:

```text
16A_LIVE_ACCOUNT_READINESS_AND_RISK_ACCEPTANCE_AUDIT
```

目的:

```text
本番口座で自動売買をONにする前の最終確認。
```

16B:

```text
16B_LIVE_GUARDED_AUTOTRADE_MINIMUM_RISK_ROLLOUT
```

目的:

```text
最小riskで本番自動売買を限定開始する。
```

16C:

```text
16C_LIVE_AUTOTRADE_WEEKLY_PERFORMANCE_AUDIT
```

目的:

```text
週次で勝率、PF、損益、component別成績、異常ログを監査する。
```

---

## 5. 現時点でのcomponent別完成への道筋

### CoreA

現状:

```text
historical SOT = ready
live evaluator = blocked
```

主ブロッカー:

```text
A gate未凍結
tail_hard / top5 / all-consensus / stack KEEP の明示条件不足
B/Cは部分的に実装可能だが CoreA_REJECT順序とfeature/asof parityが必要
```

完成への道:

```text
A gateを実行可能条件に落とせる -> CoreA live候補
落とせない -> CoreA historical-only またはB/C限定候補を別管理
```

### CoreB

現状:

```text
historical SOT = allowed
live evaluator = blocked
```

主ブロッカー:

```text
same_count / cluster_id の元クラスタリング実装なし
row-level cluster membership ledgerなし
raw ledgerからの近似再構成は失敗
```

完成への道:

```text
original clustering algorithm or membership ledgerが見つかる -> replay parity後にlive候補
見つからない -> CoreB historical-only
```

現在判断:

```text
CoreBは当面 historical-only / live blocked
```

### MEDIUM

現状:

```text
arbitration replay = OK
live evaluator = blocked
```

主ブロッカー:

```text
TIER2_HVT manifest mismatch
feature/asof parity未証明
CoreA/CoreB HIGH arbitration dependency
```

完成への道:

```text
RANGE96_REFINED / VOL_TRMEAN32_REFINED:
  manifest一致済み。feature/asof parityが通ればlive候補。

TIER2_HVT:
  13D-2 / 13D-3で reconciled rule / split variants / historical-only のどれかを決める。
```

---

## 6. 最終成果物の想定

最終的にrepoに置きたいもの:

```text
configs/gold_v2/live_evaluator_components_YYYYMMDD.json
configs/gold_v2/live_risk_config_YYYYMMDD.json
configs/gold_v2/discord_notification_template_YYYYMMDD.json
configs/gold_v2/mt5_autotrade_guard_config_YYYYMMDD.json

scripts/gold_v2_runtime/run_gold_v2_live_candidate_evaluator.py
scripts/gold_v2_runtime/run_gold_v2_discord_notifier.py
scripts/gold_v2_runtime/run_gold_v2_mt5_guarded_autotrader.py
scripts/gold_v2_runtime/run_gold_v2_position_monitor.py
scripts/gold_v2_runtime/run_gold_v2_trade_lifecycle_audit.py
```

最終運用出力:

```text
Files\FX_OUTPUTS\gold_v2_live_runtime\live_candidate_rows.csv
Files\FX_OUTPUTS\gold_v2_live_runtime\discord_notification_log.csv
Files\FX_OUTPUTS\gold_v2_live_runtime\mt5_order_request_log.csv
Files\FX_OUTPUTS\gold_v2_live_runtime\mt5_order_result_log.csv
Files\FX_OUTPUTS\gold_v2_live_runtime\position_monitor_log.csv
Files\FX_OUTPUTS\gold_v2_live_runtime\trade_lifecycle_ledger.csv
Files\FX_OUTPUTS\gold_v2_live_runtime\safety_state.json
```

---

## 7. 絶対に抜けてはいけない安全装置

MT5自動売買に進む前に必須。

```text
1. demo/live明示フラグ
2. user_confirmed_live_autotrade フラグ
3. max_lot
4. max_positions
5. max_daily_trades
6. max_daily_loss
7. max_spread
8. symbol whitelist
9. magic number固定
10. duplicate signal guard
11. cooldown
12. position already exists guard
13. no MT5 position match handling
14. emergency stop file
15. order_send failure logging
16. order_result retcode handling
17. manual close handling
18. partial close handling
19. weekend/market closed guard
20. clock/timezone consistency
```

---

## 8. 次チャットでの正しい言い方

```text
完成形は Discord通知 + MT5 guarded autotrading です。
ただし現時点ではまだ audit-only で、13D-2から再開してください。
dry-run evaluator は中間ゲートであり、最終完成ではありません。
13D-2以降は、13E/13F/13Gでlive eligible componentsを確定し、
14A〜14Dでdry-run候補・通知preview・MT5 order preview・safety gateを作り、
その後15A〜15EでDiscord実通知とMT5デモ guarded autotrade、
最後に16系で本番guarded autotradeへ進める設計にしてください。
```

---

## 9. 今すぐ次にやること

今すぐやることは変わらない。

```text
13D2_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY
```

ただし、13D-2以降のゴールは以下に修正済み。

```text
中間目標:
  GOLD_V2_LIVE_DRY_RUN_EVALUATOR_READY_NO_EXTERNAL_ACTIONS

最終目標:
  GOLD_V2_DISCORD_NOTIFIED_MT5_GUARDED_AUTOTRADE_READY
```
