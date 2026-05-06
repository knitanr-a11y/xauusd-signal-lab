# NEXT CHAT HANDOFF - MOCHIPOYO MINIMAL LIVE

最終更新: 2026-05-06

このドキュメントは、次チャットで `もちぽよ式 GOLD minimal live / Discord / MT5 demo auto-trade` の続きから始めるための引き継ぎである。

---

## 1. 次チャットで最初に読むファイル

必ず以下を読む。

```text
docs/NEXT_CHAT_HANDOFF.md
docs/NEXT_CHAT_HANDOFF_MOCHIPOYO_MINIMAL_LIVE.md
docs/MOCHIPOYO_GOLD_MINIMAL_LIVE_ONCE_STABILITY.md
docs/MOCHIPOYO_MINIMAL_LEDGER_VALIDATION.md
docs/MOCHIPOYO_MINIMAL_RISK_NOTIFICATION_VALIDATION.md
docs/MOCHIPOYO_MINIMAL_SCANNER_VALIDATION_LOG.md
docs/MOCHIPOYO_MINIMAL_AUTOTRADE_VALIDATION.md
```

BTCを触る場合は以下も読む。

```text
docs/IMPORTANT_BTC_SPREAD_REVALIDATION.md
```

---

## 2. 現在の到達点

GOLD 3pair のもちぽよ式 minimal live flow は、Discord実送信、MT5デモ口座へのauto-trade sendまでPASS扱い。

対象pair:

```text
GOLD_H4_M5_SCALP
GOLD_H4_M15_DAYTRADE
GOLD_D1_H1_DAYTRADE
```

総合判定:

```text
GOLD candidate generation: PASS
GOLD risk enrich: PASS
GOLD notification eligibility: PASS
GOLD trigger window filter: PASS
GOLD ledger duplicate filter: PASS
GOLD pair trigger state: PASS
GOLD minimal live once stability: PASS
GOLD minimal live dry loop: PASS
Discord compact message: PASS
Discord実送信: PASS
order payload generation: PASS
MT5 demo connection: PASS
GOLD# symbol/tick: PASS
MT5 order_check: PASS
MT5 demo single order_send: PASS
position policy guards: PASS
live loop auto-trade dry-run: PASS
live loop auto-trade send: PASS
live loop auto-trade duplicate/position block: PASS
```

重要:

```text
本口座での自動売買は未実施。
検証済みの実発注は XMTrading デモ口座 75539039 のみ。
```

---

## 3. 追加・修正済みファイル

主な追加/修正ファイル:

```text
scripts/apply_mochipoyo_pair_trigger_state.py
scripts/run_mochipoyo_gold_minimal_live_once.py
scripts/run_mochipoyo_gold_minimal_live_loop_dry.py
scripts/check_mt5_connection_and_symbol.py
scripts/check_mt5_order_payloads.py
scripts/build_mochipoyo_order_payloads.py
scripts/send_mt5_order_from_payload.py
```

関連して既に使っている既存/追加部品:

```text
scripts/mochipoyo_minimal_scanner.py
scripts/mochipoyo_candidate_generators.py
scripts/apply_mochipoyo_notification_eligibility.py
scripts/apply_mochipoyo_notification_ledger.py
scripts/send_mochipoyo_discord_messages.py
scripts/mochipoyo_risk_enricher.py
scripts/mochipoyo_notification_filter.py
```

重要コミット例:

```text
023c0e6507838b530715817f1a4b0c9397bde0e6
  Add dry loop wrapper for GOLD minimal live once

43ad4f240cdbcf11bd33e9ff7df631e6ea347aa7
  Add read-only MT5 connection/symbol checker

130a1444de47eeaffc2ddb53ea0ce4b5073e6a56
  Accept MT5 order_check retcode 0 Done as pass

3d80e86481c1fae60f50b41d57ed68060bcee295
  Add guarded MT5 order sender for demo payload tests

5558ab9e9865ccad6be05a5e7aeef4b0a77efa1d
  Add MT5 position policy guards for same-direction scaling

6ab99c54662126bd4be74e7ba81d675eea346eb3
  Add MT5 auto-trade dry-run stage to minimal live loop

22fc044146ca8f6ecf9a47b932c5ab0712938fba
  Treat auto-trade dry-run position-policy blocks as safe skips

fd4accb841c1d17c63c8ccc18f83dc51f8c703bf
  Add guarded MT5 auto-trade send mode to live loop

623ad0aeb230ee062574804054ffb74df61ae132
  Document Mochipoyo minimal auto-trade validation
```

---

## 4. GOLD pair trigger state の仕様

常時稼働時に毎回全pairをscanしない。
CSVの最新確定足 `close_time` が更新されたpairだけ処理する。

GOLD pair別trigger timeframe:

```text
GOLD_H4_M5_SCALP:
  trigger_timeframe = M5
  M5 close_time 更新時だけscan

GOLD_H4_M15_DAYTRADE:
  trigger_timeframe = M15
  M15 close_time 更新時だけscan

GOLD_D1_H1_DAYTRADE:
  trigger_timeframe = H1
  H1 close_time 更新時だけscan
```

state CSV:

```text
data/results/mochipoyo/minimal_trigger_test/gold_pair_trigger_state.csv
```

---

## 5. trigger更新窓フィルターの仕様

`run_mochipoyo_gold_minimal_live_once.py` は、scanで見つかった全候補をそのままledger/Discordへ流さない。

live通知候補としてledgerへ渡す条件:

```text
previous_close_time < signal_close_time <= latest_close_time
```

理由:

```text
初回scanされたpairで、過去の候補がledger未登録という理由だけで新規通知される事故を防ぐため。
```

対策済み:

```text
trigger更新窓外の候補は notification_outside_trigger_window へ落とす。
ledgerにもDiscordにもMT5発注にも流さない。
```

このフィルターは無効化しない。

---

## 6. Discord通知の現在仕様

Discord compact message は簡素化済み。

現在の例:

```text
🟨 GOLD BUY 📈
━━━━━━━━━━━━━━
MT5時間: 2026-05-06 08:00
足: H4 → M15
戦略: H4 → M15 デイトレ / B条件

Entry: 4648.770
SL:    4546.230
TP:    4771.818
RR:    1.20

根拠:
・...

注意:
・特になし

照合ID: GOLD / GOLD_H4_M15_DAYTRADE / B / BUY / 2026-05-06 08:00 / 4648.77
```

削ったもの:

```text
Signal確定の重複表示
Pair/Rank/Keyの長い内部表現
形: - / 買い候補
```

Discord実送信はPASS済み。

---

## 7. MT5 / auto-trade の現在仕様

詳細ログは必ず以下を読む。

```text
docs/MOCHIPOYO_MINIMAL_AUTOTRADE_VALIDATION.md
```

現在のMT5デモ情報:

```text
account_login: 75539039
account_server: XMTrading-MT5 3
account_name: Demo Account
broker_symbol: GOLD#
volume_min: 0.01
volume_step: 0.01
```

live loopに追加済み:

```text
--enable-auto-trade-dry-run
--enable-auto-trade-send
--auto-trade-broker-symbol
--auto-trade-order-ledger-csv
--auto-trade-expected-login
--auto-trade-select-symbol
--auto-trade-require-demo-account
--auto-trade-position-policy
--auto-trade-max-symbol-positions
--auto-trade-max-symbol-lot
--auto-trade-max-orders
--auto-trade-deviation
```

安全仕様:

```text
--enable-auto-trade-send を明示した時だけ send_mt5_order_from_payload.py に --send を渡す
--enable-auto-trade-dry-run と --enable-auto-trade-send の同時指定は禁止
--enable-auto-trade-send では --auto-trade-expected-login が必須
--enable-auto-trade-send では --auto-trade-require-demo-account が必須
order_key重複 / account / demo / position_policy / order_check ガードを通った時だけ発注
```

position policy:

```text
block_any:
  既存ポジションが1件でもあれば停止

allow_same_direction:
  同方向ポジションだけ追加許可
  逆方向は停止
  max-symbol-positions / max-symbol-lot で制限

allow_any_until_max:
  BUY/SELL問わず最大数・最大lotまで許可
```

現時点の推奨:

```text
--auto-trade-position-policy block_any
--auto-trade-max-symbol-positions 1
--auto-trade-max-symbol-lot 0.01
--auto-trade-max-orders 1
```

---

## 8. 直近の重要成功検証

### 8.1 live loop auto-trade dry-run flat

ポジション0状態で実行。

結果:

```text
discord_status = SENT
order_payload_status = OK
order_payload_rows = 1
valid_order_payloads = 1
auto_trade_status = OK
auto_trade_send_enabled = False
auto_trade_rows = 1
auto_trade_dry_run_check_ok_rows = 1
auto_trade_blocked_position_policy_rows = 0
auto_trade_order_send_called_count = 0
auto_trade_sent_rows = 0
success = True
```

### 8.2 live loop auto-trade send

ポジション0状態で実行。

結果:

```text
discord_status = SENT
order_payload_status = OK
order_payload_rows = 1
valid_order_payloads = 1
auto_trade_status = SENT
auto_trade_send_enabled = True
auto_trade_rows = 1
auto_trade_order_send_called_count = 1
auto_trade_sent_rows = 1
success = True
```

MT5取引タブ確認:

```text
GOLD# BUY 0.01 が実際に表示された。
```

### 8.3 live loop auto-trade send duplicate/position block

既存 `GOLD# BUY 0.01` がある状態で再実行。

結果:

```text
discord_status = SENT
order_payload_status = OK
order_payload_rows = 1
valid_order_payloads = 1
auto_trade_status = OK_BLOCKED_POSITION_POLICY
auto_trade_send_enabled = True
auto_trade_rows = 1
auto_trade_blocked_position_policy_rows = 1
auto_trade_order_send_called_count = 0
auto_trade_sent_rows = 0
success = True
```

判定:

```text
既存ポジションありの追加発注ブロック: PASS
```

---

## 9. Windows long path 対応

MT5のMQL5/Files配下はパスが長く、dry loopの深い出力先では `pandas.to_csv()` が `FileNotFoundError` になることがあった。

対応済み:

```text
Windowsでは CSV保存時に \\?\ 付き extended-length path を使う
iteration開始時に scan/notification/ledger/discord/order/auto_trade を事前作成
```

検証時は短いout-dirを使う。

推奨:

```text
data/ml_loop_runX
data/ml_loop_demo_prodX
```

避けたい長いout-dir:

```text
data/results/mochipoyo/minimal_live_loop_... の深い階層
```

---

## 10. 次にやること

次の推奨は、デモ口座で短時間の auto-trade send loop。

目的:

```text
人工stateではなく、通常のtrigger更新に合わせて
no-row / outside-window / sent / blocked の挙動を確認する。
```

推奨条件:

```text
account: XMTrading demo 75539039
broker_symbol: GOLD#
lot: 0.01
position_policy: block_any
max_symbol_positions: 1
max_symbol_lot: 0.01
auto_trade_max_orders: 1
out-dir: data/ml_loop_demo_prod1 など短いパス
```

実行前に確認:

```text
MT5がデモ口座 75539039 でログイン中
Algo Trading ON
本口座ではない
既存GOLD#ポジションの有無を把握している
```

---

## 11. まだやっていないこと

```text
本口座での自動売買
長時間のデモ auto-trade send loop
損益/ポジション管理
自動決済
建値移動
トレーリング
約定後のDiscord追跡通知
ポジション一覧監視
日次損失制限
連続発注間隔制限
時間帯停止
```

現状はエントリー自動発注まで。
決済はSL/TPをMT5注文に付けているのみ。

---

## 12. 次チャットでやってはいけないこと

```text
- 本口座でいきなり --enable-auto-trade-send を使う
- expected-loginなしでauto-trade sendを許す
- require-demo-accountなしでauto-trade sendを許す
- trigger更新窓フィルターを無効化する
- 既存の run_mochipoyo_live_notify_loop.py / run_mochipoyo_live_notify_loop_light.py を使う
- 長い out-dir を使ってWindows path問題を再発させる
- notification_outside_trigger_window を通知/発注候補として扱う
```

---

## 13. 次の判断基準

短時間デモ auto-trade send loopが安定した後の次候補:

```text
1. ポジション監視スクリプト追加
2. order ledgerとMT5履歴の照合
3. 約定後Discord追跡通知
4. 日次損失制限・最大発注数制限
5. デモ1日稼働
6. 本口座検討はその後
```
