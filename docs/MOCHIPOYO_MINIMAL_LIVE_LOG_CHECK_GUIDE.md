# MOCHIPOYO MINIMAL LIVE LOG CHECK GUIDE

最終更新: 2026-05-06

このドキュメントは、もちぽよ式 GOLD minimal live / Discord / MT5 demo auto-trade loop のログ確認方法をまとめる。

対象:

```text
run_mochipoyo_gold_minimal_live_loop_dry.py
run_mochipoyo_gold_demo_autotrade_short.bat
ユーザー作成の run_mochipoyo_gold_minimal_live.bat / forever local bat
```

---

## 1. 一番重要なログ

loopの最重要ログは `--out-dir` 配下の summary CSV。

例:

```text
data\ml_loop_demo_prod_forever\gold_minimal_live_loop_live_summary.csv
```

`--out-dir` が違う場合は、先頭部分だけ置き換える。

```text
--out-dir data\ml_loop_demo_prod_short
  → data\ml_loop_demo_prod_short\gold_minimal_live_loop_live_summary.csv

--out-dir data\ml_loop_demo_prod_forever
  → data\ml_loop_demo_prod_forever\gold_minimal_live_loop_live_summary.csv
```

---

## 2. summary CSV の見方

確認コマンド:

```cmd
python -c "import pandas as pd; p=r'data\ml_loop_demo_prod_forever\gold_minimal_live_loop_live_summary.csv'; df=pd.read_csv(p,encoding='utf-8-sig'); cols=[c for c in ['loop_iteration','returncode','pairs_to_scan','notification_ok_live_rows','ledger_new_candidates','discord_status','order_payload_status','auto_trade_status','auto_trade_send_enabled','auto_trade_order_send_called_count','auto_trade_sent_rows','success'] if c in df.columns]; print(df.tail(30)[cols].to_string(index=False))"
```

重要列:

```text
loop_iteration
  loopの何回目か。

returncode
  0ならそのiterationのメイン処理は正常。

pairs_to_scan
  trigger close_time が更新されてscan対象になったpair数。
  0なら新しい確定足がない。

notification_ok_live_rows
  trigger更新窓内で通知対象になった候補数。
  0ならDiscord通知・発注候補なし。

ledger_new_candidates
  通知ledger上で新規と判定された候補数。
  0なら新規通知/新規発注対象なし。

discord_status
  SENT: Discord送信あり。
  SKIPPED_NO_ROWS: 送信候補なし。
  ERROR: Discord段でエラー。

order_payload_status
  OK: 注文payload生成あり。
  SKIPPED_NO_ROWS: 注文payload生成対象なし。
  ERROR系: payload生成段でエラー。

auto_trade_status
  SENT: MT5 order_send 実行・成功。
  OK: dry-run/order_check OK。
  OK_BLOCKED_POSITION_POLICY: 既存ポジション等で安全に発注ブロック。
  SKIPPED_NO_ORDER_PAYLOAD_ROWS: 発注payloadなしのためauto-trade段もskip。
  ERROR系: auto-trade段でエラー。

auto_trade_send_enabled
  Trueなら auto-trade send モードが有効。
  Falseなら dry-run。

auto_trade_order_send_called_count
  MT5 order_send を呼んだ回数。
  実発注の有無を見る最重要列。

auto_trade_sent_rows
  MT5 order_send 成功行数。

success
  そのiterationが正常扱いか。
```

---

## 3. よくある正常パターン

### 3.1 候補なし / 全段safe skip

```text
notification_ok_live_rows = 0
ledger_new_candidates = 0
discord_status = SKIPPED_NO_ROWS
order_payload_status = SKIPPED_NO_ROWS
auto_trade_status = SKIPPED_NO_ORDER_PAYLOAD_ROWS
auto_trade_order_send_called_count = 0
auto_trade_sent_rows = 0
success = True
```

意味:

```text
通知候補なし
Discord送信なし
order payload生成なし
MT5発注なし
正常
```

### 3.2 候補あり / Discord送信 / MT5発注成功

```text
notification_ok_live_rows >= 1
ledger_new_candidates >= 1
discord_status = SENT
order_payload_status = OK
auto_trade_status = SENT
auto_trade_order_send_called_count = 1
auto_trade_sent_rows = 1
success = True
```

意味:

```text
通知候補あり
Discord送信あり
order payload生成あり
MT5 demo order_send成功
```

この時はMT5取引タブでもポジションを確認する。

### 3.3 候補あり / 既存ポジションあり / 発注ブロック

```text
notification_ok_live_rows >= 1
ledger_new_candidates >= 1
discord_status = SENT
order_payload_status = OK
auto_trade_status = OK_BLOCKED_POSITION_POLICY
auto_trade_order_send_called_count = 0
auto_trade_sent_rows = 0
success = True
```

意味:

```text
通知とpayload生成はした
しかし既存GOLD#ポジション等により block_any が発動
order_sendは呼ばれていない
追加発注なし
正常な安全停止
```

---

## 4. 危険/要確認パターン

### 4.1 success が False

```text
success = False
```

見るもの:

```text
returncode
discord_status
order_payload_status
auto_trade_status
```

次に iteration folder の stderr を見る。

例:

```text
data\ml_loop_demo_prod_forever\iter_0007\once_stderr.txt
data\ml_loop_demo_prod_forever\iter_0007\discord\discord_send_stderr.txt
data\ml_loop_demo_prod_forever\iter_0007\order\order_payload_stderr.txt
data\ml_loop_demo_prod_forever\iter_0007\auto_trade\auto_trade_stderr.txt
```

### 4.2 order_send が呼ばれている

```text
auto_trade_order_send_called_count > 0
```

これはデモ口座で実発注が呼ばれたという意味。

確認する:

```text
auto_trade_sent_rows
MT5取引タブ
order ledger
```

### 4.3 order_send が呼ばれたのに success が False

```text
auto_trade_order_send_called_count > 0
auto_trade_sent_rows = 0
success = False
```

これは order_send 失敗の可能性がある。

見るファイル:

```text
data\ml_loop_demo_prod_forever\iter_xxxx\auto_trade\mt5_order_send_results.csv
data\ml_loop_demo_prod_forever\iter_xxxx\auto_trade\mt5_order_send_report.json
data\ml_loop_demo_prod_forever\iter_xxxx\auto_trade\auto_trade_stdout.txt
data\ml_loop_demo_prod_forever\iter_xxxx\auto_trade\auto_trade_stderr.txt
```

---

## 5. iteration別ログ構造

`--out-dir data\ml_loop_demo_prod_forever` の場合:

```text
data\ml_loop_demo_prod_forever\
  gold_minimal_live_loop_live_summary.csv
  gold_minimal_live_loop_live_events.csv
  gold_minimal_live_loop_live_final.csv
  iter_0001\
    once_command.txt
    once_stdout.txt
    once_stderr.txt
    minimal_live_once_summary.csv
    scan\
    notification\
    ledger\
    discord\
    order\
      order_payload_command.txt
      order_payload_stdout.txt
      order_payload_stderr.txt
      order_payloads.csv
      order_payloads.json
    auto_trade\
      auto_trade_command.txt
      auto_trade_stdout.txt
      auto_trade_stderr.txt
      mt5_order_send_results.csv
      mt5_order_send_report.json
```

見る優先順位:

```text
1. gold_minimal_live_loop_live_summary.csv
2. 問題があるiterationの minimal_live_once_summary.csv
3. 問題があるstageの *_stderr.txt
4. auto_trade の mt5_order_send_results.csv / report.json
```

---

## 6. Discord通知ledger

通知ledgerはコマンドの `--notification-ledger-csv` で指定している。

現在のproduction系:

```text
data\results\mochipoyo\minimal_live_once_test\gold_notification_ledger.csv
```

役割:

```text
同じpayload_keyの通知重複を防ぐ
過去に通知済みの候補を記録する
```

確認例:

```cmd
python -c "import pandas as pd; p=r'data\results\mochipoyo\minimal_live_once_test\gold_notification_ledger.csv'; df=pd.read_csv(p,encoding='utf-8-sig'); print(df.tail(20).to_string(index=False))"
```

---

## 7. MT5注文ledger

MT5注文ledgerはコマンドの `--auto-trade-order-ledger-csv` で指定している。

現在のproduction demo系:

```text
data\mt5_demo_order_test\goldsharp_auto_trade_demo_prod_order_ledger.csv
```

役割:

```text
order_keyの二重発注を防ぐ
Pythonからorder_sendした記録を残す
order_ticket / deal_ticket を残す
```

確認例:

```cmd
python -c "import pandas as pd; p=r'data\mt5_demo_order_test\goldsharp_auto_trade_demo_prod_order_ledger.csv'; df=pd.read_csv(p,encoding='utf-8-sig'); print(df.tail(20).to_string(index=False))"
```

注意:

```text
MT5で手動決済した結果や最終損益は、このorder ledgerにはまだ自動取り込みしていない。
決済履歴・損益はMT5の口座履歴側を見る。
```

---

## 8. 現在のログ例

ユーザー確認ログ:

```text
loop_iteration 1:
  returncode = 0
  pairs_to_scan = 2
  notification_ok_live_rows = 0
  ledger_new_candidates = 0
  discord_status = SKIPPED_NO_ROWS
  order_payload_status = SKIPPED_NO_ROWS
  auto_trade_status = SKIPPED_NO_ORDER_PAYLOAD_ROWS
  auto_trade_send_enabled = True
  auto_trade_order_send_called_count = 0
  auto_trade_sent_rows = 0
  success = True

loop_iteration 2-7:
  returncode = 0
  pairs_to_scan = 0 または 1
  notification_ok_live_rows = 0
  ledger_new_candidates = 0
  discord_status = SKIPPED_NO_ROWS
  order_payload_status = SKIPPED_NO_ROWS
  auto_trade_status = SKIPPED_NO_ORDER_PAYLOAD_ROWS
  auto_trade_order_send_called_count = 0
  auto_trade_sent_rows = 0
  success = True
```

判定:

```text
forever demo loopは稼働中。
ここまで通知候補なし。
発注なし。
全iteration正常。
```

---

## 9. 今後追加したいログ機能

まだ未実装:

```text
MT5ポジション一覧の定期snapshot
MT5口座履歴の自動取得
決済済み損益のCSV化
order_ticket / deal_ticket とMT5履歴の自動照合
約定後Discord追跡通知
```

次に追加するなら:

```text
scripts/check_mt5_open_positions.py
scripts/export_mt5_deal_history.py
```

まずはポジション監視ログを追加するのが安全。
