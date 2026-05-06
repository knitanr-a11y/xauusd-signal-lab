# MOCHIPOYO GOLD Minimal Live Once Stability Validation

最終更新: 2026-05-06

このドキュメントは、`scripts/run_mochipoyo_gold_minimal_live_once.py` の修正後安定確認ログである。

関連ログ:

```text
docs/MOCHIPOYO_MINIMAL_LEDGER_VALIDATION.md
docs/MOCHIPOYO_MINIMAL_RISK_NOTIFICATION_VALIDATION.md
docs/MOCHIPOYO_MINIMAL_SCANNER_VALIDATION_LOG.md
```

---

## 1. 対象スクリプト

```text
scripts/run_mochipoyo_gold_minimal_live_once.py
```

このスクリプトは常時ループではない。
GOLD minimal live flow を1回だけ実行する単発CLIである。

接続順:

```text
pair trigger state
  -> should_scan=True のGOLD pairだけscan
  -> risk enrich
  -> notification eligibility
  -> trigger更新窓フィルター
  -> ledger duplicate filter
  -> Discord dry-run / no-row skip
  -> 成功後だけ trigger state を進める
```

---

## 2. 修正後の重要仕様

### 2.1 trigger更新窓フィルター

ledgerへ流す通知候補は、以下を満たすものだけにする。

```text
previous_close_time < signal_close_time <= latest_close_time
```

目的:

```text
初回scanされたpairの過去候補が、ledger未登録という理由だけで新規通知される事故を防ぐ。
```

例:

```text
previous_close_time = 2026-05-06 12:00:00
latest_close_time   = 2026-05-06 13:00:00
```

通知対象になるのは以下だけ。

```text
2026-05-06 12:00:00 より後
かつ
2026-05-06 13:00:00 以下
```

それより古い候補は `notification_outside_trigger_window` に落とし、ledgerにもDiscordにも流さない。

### 2.2 送信候補0件の扱い

`to_send` が0件の場合、Discord dry-runを呼ばない。

```text
discord_status = SKIPPED_NO_ROWS
discord_returncode = 0
success = True
```

目的:

```text
更新なし、またはlive window内候補なしの正常ケースをエラー扱いしない。
```

---

## 3. run5: 修正後確認

実行:

```cmd
python scripts\run_mochipoyo_gold_minimal_live_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\results\mochipoyo\minimal_live_once_test\run5 --symbol GOLD --trigger-state-csv data\results\mochipoyo\minimal_trigger_test\gold_pair_trigger_state.csv --notification-ledger-csv data\results\mochipoyo\minimal_live_once_test\gold_notification_ledger.csv --commit-trigger-state --commit-ledger --discord-dry-run --run-id gold_minimal_live_once_5
```

結果:

```text
pairs_total = 3
pairs_to_scan = 1
scan_errors = 0
notification_ok_live_rows = 0
notification_outside_trigger_window_rows = 37
ledger_new_candidates = 0
ledger_skipped_rows = 0
ledger_append_rows = 0
commit_ledger = True
discord_dry_run = True
discord_status = SKIPPED_NO_ROWS
discord_returncode = 0
commit_trigger_state = True
trigger_state_advanced = True
trigger_window_filter_enabled = True
success = True
```

判定:

```text
scanされたpairには過去候補37件があったが、すべてtrigger更新窓外として除外。
ledgerにもDiscordにも流れていない。
送信候補0件のためDiscord dry-runは SKIPPED_NO_ROWS として正常skip。
success=True。
```

---

## 4. run6: M5更新時の安定確認

実行:

```cmd
python scripts\run_mochipoyo_gold_minimal_live_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\results\mochipoyo\minimal_live_once_test\run6 --symbol GOLD --trigger-state-csv data\results\mochipoyo\minimal_trigger_test\gold_pair_trigger_state.csv --notification-ledger-csv data\results\mochipoyo\minimal_live_once_test\gold_notification_ledger.csv --commit-trigger-state --commit-ledger --discord-dry-run --run-id gold_minimal_live_once_6
```

結果:

```text
pairs_total = 3
pairs_to_scan = 1
scan_errors = 0
notification_ok_live_rows = 0
notification_outside_trigger_window_rows = 37
ledger_new_candidates = 0
ledger_skipped_rows = 0
ledger_append_rows = 0
commit_ledger = True
discord_dry_run = True
discord_status = SKIPPED_NO_ROWS
discord_returncode = 0
commit_trigger_state = True
trigger_state_advanced = True
trigger_window_filter_enabled = True
success = True
```

scan対象:

```text
GOLD_H4_M5_SCALP:
  trigger_timeframe   = M5
  previous_close_time = 2026-05-06 13:05:00
  latest_close_time   = 2026-05-06 13:10:00
  trigger_status      = SCAN_REQUIRED
  trigger_reason      = new confirmed trigger close_time
```

判定:

```text
M5更新により GOLD_H4_M5_SCALP だけがscan対象になった。
過去候補37件はすべてtrigger更新窓外として除外。
ledger_new_candidates = 0 / ledger_append_rows = 0。
送信候補0件のため Discord は SKIPPED_NO_ROWS。
success=True。
```

---

## 5. run7: M5 + M15更新時の安定確認

実行:

```cmd
python scripts\run_mochipoyo_gold_minimal_live_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\results\mochipoyo\minimal_live_once_test\run7 --symbol GOLD --trigger-state-csv data\results\mochipoyo\minimal_trigger_test\gold_pair_trigger_state.csv --notification-ledger-csv data\results\mochipoyo\minimal_live_once_test\gold_notification_ledger.csv --commit-trigger-state --commit-ledger --discord-dry-run --run-id gold_minimal_live_once_7
```

結果:

```text
pairs_total = 3
pairs_to_scan = 2
scan_errors = 0
notification_ok_live_rows = 0
notification_outside_trigger_window_rows = 44
ledger_new_candidates = 0
ledger_skipped_rows = 0
ledger_append_rows = 0
commit_ledger = True
discord_dry_run = True
discord_status = SKIPPED_NO_ROWS
discord_returncode = 0
commit_trigger_state = True
trigger_state_advanced = True
trigger_window_filter_enabled = True
success = True
```

scan対象:

```text
GOLD_H4_M5_SCALP:
  trigger_timeframe   = M5
  previous_close_time = 2026-05-06 13:10:00
  latest_close_time   = 2026-05-06 13:15:00
  trigger_status      = SCAN_REQUIRED

GOLD_H4_M15_DAYTRADE:
  trigger_timeframe   = M15
  previous_close_time = 2026-05-06 13:00:00
  latest_close_time   = 2026-05-06 13:15:00
  trigger_status      = SCAN_REQUIRED
```

判定:

```text
M5更新により GOLD_H4_M5_SCALP がscan対象。
M15更新により GOLD_H4_M15_DAYTRADE もscan対象。
過去候補44件はすべてtrigger更新窓外として除外。
ledger_new_candidates = 0 / ledger_append_rows = 0。
送信候補0件のため Discord は SKIPPED_NO_ROWS。
success=True。
```

---

## 6. 安定確認まとめ

run5〜run7 の結果:

```text
run5:
  pairs_to_scan = 1
  notification_ok_live_rows = 0
  notification_outside_trigger_window_rows = 37
  ledger_new_candidates = 0
  discord_status = SKIPPED_NO_ROWS
  success = True

run6:
  pairs_to_scan = 1
  notification_ok_live_rows = 0
  notification_outside_trigger_window_rows = 37
  ledger_new_candidates = 0
  discord_status = SKIPPED_NO_ROWS
  success = True

run7:
  pairs_to_scan = 2
  notification_ok_live_rows = 0
  notification_outside_trigger_window_rows = 44
  ledger_new_candidates = 0
  discord_status = SKIPPED_NO_ROWS
  success = True
```

確認できたこと:

```text
1. pair別triggerは期待どおり動作。
2. M5更新時は GOLD_H4_M5_SCALP がscan対象になる。
3. M15更新時は GOLD_H4_M15_DAYTRADE もscan対象になる。
4. trigger更新窓外の過去候補は notification_outside_trigger_window に落ちる。
5. trigger更新窓外候補は ledger に流れない。
6. trigger更新窓外候補は Discord に流れない。
7. to_send 0件では Discord dry-run は SKIPPED_NO_ROWS として正常skip。
8. success=True の時だけ trigger_state_advanced=True。
```

---

## 7. GOLD minimal live once 総合判定

```text
GOLD_H4_M5_SCALP:
  candidate generation PASS
  risk enrich PASS
  notification eligibility PASS
  trigger window filter PASS
  ledger duplicate filter PASS
  Discord dry-run / no-row skip PASS
  pair trigger state PASS
  minimal live once stability PASS

GOLD_H4_M15_DAYTRADE:
  candidate generation PASS
  risk enrich PASS
  notification eligibility PASS
  trigger window filter PASS
  ledger duplicate filter PASS
  Discord dry-run / no-row skip PASS
  pair trigger state PASS
  minimal live once stability PASS

GOLD_D1_H1_DAYTRADE:
  candidate generation PASS
  risk enrich PASS
  notification eligibility PASS
  trigger window filter PASS
  ledger duplicate filter PASS
  Discord dry-run / no-row skip PASS
  pair trigger state PASS
  minimal live once stability PASS
```

結論:

```text
GOLD 3pair は、単発 minimal live flow の安定確認までPASS扱い。
次は、常時稼働ループ化する前に、Discord実送信を行わない light loop / scheduler 相当のdry-run制御を作る。
```

---

## 8. 次の作業

常時稼働化の前段として、以下を作る。

```text
scripts/run_mochipoyo_gold_minimal_live_loop_dry.py
```

目的:

```text
一定間隔で run_mochipoyo_gold_minimal_live_once.py 相当の処理を呼ぶ。
Discord実送信はまだ行わない。
自動売買もしない。
Ctrl+Cで安全終了する。
各iterationの summary を append ledger として保存する。
```

注意:

```text
既存の run_mochipoyo_live_notify_loop.py / run_mochipoyo_live_notify_loop_light.py は使わない。
新しい minimal live loop は、今回検証済みの単発flowを薄く繰り返す制御層として作る。
```
