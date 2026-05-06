# MOCHIPOYO GOLD Minimal Live Once Stability Validation

最終更新: 2026-05-06

このドキュメントは、`scripts/run_mochipoyo_gold_minimal_live_once.py` と `scripts/run_mochipoyo_gold_minimal_live_loop_dry.py` の修正後安定確認ログである。

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
scripts/run_mochipoyo_gold_minimal_live_loop_dry.py
```

`run_mochipoyo_gold_minimal_live_once.py` は常時ループではない。
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

`run_mochipoyo_gold_minimal_live_loop_dry.py` は、上記の単発CLIを一定間隔で繰り返すdry loopである。

安全方針:

```text
Discord実送信なし
自動売買なし
Ctrl+Cで安全終了
各iterationのsummaryをCSVへ追記
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

### 2.3 Windows long path 対応

MT5のMQL5/Files配下はパスが長く、dry loopではさらに以下のように階層が深くなる。

```text
...
  data/results/mochipoyo/minimal_live_loop_dry_test/runX/iter_0001/notification/...
```

そのため、Windowsの classic MAX_PATH 制限により、親ディレクトリ作成済みでも `pandas.to_csv()` が `FileNotFoundError` になるケースがあった。

対策:

```text
run_mochipoyo_gold_minimal_live_once.py のCSV保存で、Windowsの場合は \\?\ 付き extended-length path を使う。
```

また、dry loop側でも各iteration開始時に以下を先に作成する。

```text
iter_xxxx/scan
iter_xxxx/notification
iter_xxxx/ledger
iter_xxxx/discord
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

## 6. dry loop 初回検証で見つかった問題

対象:

```text
scripts/run_mochipoyo_gold_minimal_live_loop_dry.py
```

最初のdry loop実行では、各iterationで `returncode=1` となった。

エラー:

```text
FileNotFoundError:
...\iter_0001\notification\minimal_candidates_notification_outside_trigger_window_gold_h4_m5_scalp.csv
```

確認結果:

```text
run_mochipoyo_gold_minimal_live_once.py の write_csv() には p.parent.mkdir(parents=True, exist_ok=True) が入っていた。
それでも pandas.to_csv() で FileNotFoundError になっていた。
```

原因推定:

```text
Windows classic MAX_PATH 制限。
MT5 roaming profile + repo path + data/results/... + iter_0001/notification + 長いファイル名でパスが長くなりすぎた可能性が高い。
```

対策:

```text
1. run_mochipoyo_gold_minimal_live_once.py に Windows long path 対応を追加。
2. run_mochipoyo_gold_minimal_live_loop_dry.py で iteration_dir 配下の scan/notification/ledger/discord を事前作成。
3. 検証時の --out-dir を短くする。
```

---

## 7. dry loop run4: 短いout-dirで成功確認

実行:

```cmd
python scripts\run_mochipoyo_gold_minimal_live_loop_dry.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\ml_loop_run4 --symbol GOLD --trigger-state-csv data\results\mochipoyo\minimal_trigger_test\gold_pair_trigger_state.csv --notification-ledger-csv data\results\mochipoyo\minimal_live_once_test\gold_notification_ledger.csv --iterations 3 --sleep-seconds 10 --commit-trigger-state --commit-ledger
```

結果:

```text
iteration 1:
  returncode = 0
  pairs_to_scan = 2
  notification_ok_live_rows = 0
  notification_outside_trigger_window_rows = 43
  ledger_new_candidates = 0
  ledger_append_rows = 0
  discord_status = SKIPPED_NO_ROWS
  success = True

iteration 2:
  returncode = 0
  pairs_to_scan = 0
  notification_ok_live_rows = 0
  notification_outside_trigger_window_rows = 0
  ledger_new_candidates = 0
  ledger_append_rows = 0
  discord_status = SKIPPED_NO_ROWS
  success = True

iteration 3:
  returncode = 0
  pairs_to_scan = 0
  notification_ok_live_rows = 0
  notification_outside_trigger_window_rows = 0
  ledger_new_candidates = 0
  ledger_append_rows = 0
  discord_status = SKIPPED_NO_ROWS
  success = True
```

判定:

```text
dry loop run4 は成功。
1回目だけ更新pairを処理し、2回目/3回目は pairs_to_scan = 0。
trigger更新窓外候補はledger/Discordへ流れない。
to_send 0件は SKIPPED_NO_ROWS として正常終了。
```

確認できたこと:

```text
dry loop wrapper: PASS
once呼び出し: PASS
Windows long path対応: PASS
pair trigger state更新: PASS
更新なしskip: PASS
trigger window filter: PASS
Discord no-row skip: PASS
```

---

## 8. 安定確認まとめ

run5〜run7 と dry loop run4 の結果:

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

dry loop run4:
  iterations = 3
  returncode = 0 / 0 / 0
  success = True / True / True
  pairs_to_scan = 2 / 0 / 0
  discord_status = SKIPPED_NO_ROWS / SKIPPED_NO_ROWS / SKIPPED_NO_ROWS
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
9. dry loopで単発flowを複数回繰り返せる。
10. 更新なしiterationでは pairs_to_scan = 0 になる。
```

---

## 9. GOLD minimal live flow 総合判定

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
  minimal live dry loop PASS

GOLD_H4_M15_DAYTRADE:
  candidate generation PASS
  risk enrich PASS
  notification eligibility PASS
  trigger window filter PASS
  ledger duplicate filter PASS
  Discord dry-run / no-row skip PASS
  pair trigger state PASS
  minimal live once stability PASS
  minimal live dry loop PASS

GOLD_D1_H1_DAYTRADE:
  candidate generation PASS
  risk enrich PASS
  notification eligibility PASS
  trigger window filter PASS
  ledger duplicate filter PASS
  Discord dry-run / no-row skip PASS
  pair trigger state PASS
  minimal live once stability PASS
  minimal live dry loop PASS
```

結論:

```text
GOLD 3pair は、Discord実送信なしの minimal live dry loop までPASS扱い。
次は、もう少し長めのdry loop、または実Discord送信に進む前のpreview/本文確認を行う。
```

---

## 10. 次の作業

次のどちらかを行う。

### A. 長めのdry loop

```text
iterations = 12
sleep_seconds = 10〜30
```

目的:

```text
M5/M15/H1更新タイミングをまたいでも安定して動くか確認する。
```

### B. Discord本文preview確認

目的:

```text
実送信前に、通知本文が読みやすいか、payload_keyやentry情報が欠けていないか確認する。
```

まだ自動売買は行わない。
