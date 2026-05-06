# MOCHIPOYO Minimal Ledger Validation Log

最終更新: 2026-05-06

このドキュメントは、もちぽよ式 live notification minimal scanner の ledger重複判定・Discord dry-run・pair別更新トリガー・単発minimal live flow検証ログである。

関連ログ:

```text
docs/MOCHIPOYO_MINIMAL_SCANNER_VALIDATION_LOG.md
docs/MOCHIPOYO_MINIMAL_RISK_NOTIFICATION_VALIDATION.md
```

---

## 1. 目的

Discord送信へ進む前に、`payload_key` ベースで以下を保証する。

```text
1. 初回実行では未送信payload_keyだけが通知候補になる
2. ledgerへ記録後、同じCSVを再実行すると全件duplicate skipになる
3. 同一入力内に同じpayload_keyが複数存在しても、1回だけ通知候補になる
4. last_notified_time_by_symbol_pair_direction 相当のstateをCSVで確認できる
5. ledger判定後の送信候補CSVをDiscord送信スクリプトがdry-runで読める
6. pair別trigger timeframeのclose_time更新を検出できる
7. GOLD minimal live flow を単発CLIで安全に接続できる
```

この段階では Discord実送信も自動売買も行わない。

---

## 2. 実装ファイル

```text
scripts/apply_mochipoyo_notification_ledger.py
scripts/send_mochipoyo_discord_messages.py
scripts/apply_mochipoyo_pair_trigger_state.py
scripts/run_mochipoyo_gold_minimal_live_once.py
```

`apply_mochipoyo_notification_ledger.py` の役割:

```text
notification_ok CSV を入力
既存 ledger CSV を読む
payload_key を判定
NEW / DUPLICATE_EXISTING / DUPLICATE_IN_INPUT_BATCH / NOT_NOTIFICATION_ELIGIBLE / INVALID_PAYLOAD_KEY を分類
必要なら --commit-ledger で ledger CSV に追記
state CSV を出力
```

ledger判定出力:

```text
notification_ledger_classified.csv
notification_ledger_to_send.csv
notification_ledger_skipped.csv
notification_ledger_append_preview.csv
notification_ledger_state.csv
notification_ledger_summary.csv
```

`send_mochipoyo_discord_messages.py` の今回の役割:

```text
--send を付けずにdry-run実行
notification_ledger_to_send.csv を読む
payload_key を維持したまま preview_txt / preview_json を生成
Discordへは送信しない
```

`apply_mochipoyo_pair_trigger_state.py` の役割:

```text
pair別trigger timeframe CSVを読む
最新確定足 close_time を取得
state CSV の last_seen_close_time と比較
更新pairだけ should_scan=True にする
```

`run_mochipoyo_gold_minimal_live_once.py` の役割:

```text
常時ループではない単発CLI
trigger state
  -> should_scan=True のGOLD pairだけscan
  -> risk enrich
  -> notification eligibility
  -> ledger duplicate filter
  -> Discord dry-run preview
  -> 成功後だけ trigger state を進める
```

---

## 3. GOLD 3pair ledgerテスト

対象:

```text
GOLD_H4_M5_SCALP        notification_ok 37件
GOLD_H4_M15_DAYTRADE    notification_ok 7件
GOLD_D1_H1_DAYTRADE     notification_ok 2件
合計                    46件
```

入力:

```text
data/results/mochipoyo/minimal_notification_filter_test/minimal_candidates_notification_ok_gold_*.csv
```

ledger:

```text
data/results/mochipoyo/minimal_ledger_test/gold_notification_ledger.csv
```

---

## 4. 1回目 ledger 実行

実行:

```cmd
python scripts\apply_mochipoyo_notification_ledger.py --input-dir data\results\mochipoyo\minimal_notification_filter_test --pattern "minimal_candidates_notification_ok_gold_*.csv" --symbol GOLD --ledger-csv data\results\mochipoyo\minimal_ledger_test\gold_notification_ledger.csv --out-dir data\results\mochipoyo\minimal_ledger_test\run1 --commit-ledger --run-id gold_ledger_test_1
```

結果:

```text
rows_in = 46
new_candidates = 46
duplicate_existing = 0
duplicate_in_batch = 0
not_eligible = 0
invalid_payload_key = 0
ledger_append_rows = 46
commit_ledger = True
```

判定:

```text
初回実行ではGOLD notification_ok 46件すべてが新規通知候補として残った。
ledger_append_rows も46件で期待どおり。
```

---

## 5. 2回目 ledger 実行

実行:

```cmd
python scripts\apply_mochipoyo_notification_ledger.py --input-dir data\results\mochipoyo\minimal_notification_filter_test --pattern "minimal_candidates_notification_ok_gold_*.csv" --symbol GOLD --ledger-csv data\results\mochipoyo\minimal_ledger_test\gold_notification_ledger.csv --out-dir data\results\mochipoyo\minimal_ledger_test\run2 --commit-ledger --run-id gold_ledger_test_2
```

結果:

```text
rows_in = 46
new_candidates = 0
duplicate_existing = 46
duplicate_in_batch = 0
not_eligible = 0
invalid_payload_key = 0
ledger_append_rows = 0
commit_ledger = True
```

判定:

```text
同じCSVを再投入した2回目では、全46件が既存ledger重複としてskipされた。
ledger_append_rows は0件で期待どおり。
```

---

## 6. GOLD Discord dry-run

実送信は行わず、`--send` なしで preview のみ生成した。

入力:

```text
data/results/mochipoyo/minimal_ledger_test/run1/notification_ledger_to_send.csv
```

実行:

```cmd
python scripts\send_mochipoyo_discord_messages.py --input-csv data\results\mochipoyo\minimal_ledger_test\run1\notification_ledger_to_send.csv --send-ledger-csv data\results\mochipoyo\minimal_ledger_test\discord_dryrun_send_ledger.csv --preview-txt data\results\mochipoyo\minimal_ledger_test\discord_dryrun_preview.txt --preview-json data\results\mochipoyo\minimal_ledger_test\discord_dryrun_preview.json --symbol GOLD --max-rows 5 --style compact
```

結果:

```text
rows = 5
send = False
duplicates_existing = 0
dry_run_would_send = 5
sent = 0
errors = 0
preview_txt = data/results/mochipoyo/minimal_ledger_test/discord_dryrun_preview.txt
preview_json = data/results/mochipoyo/minimal_ledger_test/discord_dryrun_preview.json
```

判定:

```text
Discord dry-run は期待どおり通過。
--send を付けていないためDiscordへ実送信はされていない。
ledger判定後の notification_ledger_to_send.csv を、既存Discord送信スクリプトが読めることを確認。
preview_txt / preview_json も生成された。
```

---

## 7. GOLD pair別更新トリガー検証

目的:

```text
常時稼働ループで全pairを毎回scanしない。
CSVの最新確定足 close_time が更新されたpairだけを判定する。
```

GOLDのtrigger timeframe:

```text
GOLD_H4_M5_SCALP:
  trigger_timeframe = M5
  M5 close_time が進んだ時だけ判定

GOLD_H4_M15_DAYTRADE:
  trigger_timeframe = M15
  M15 close_time が進んだ時だけ判定

GOLD_D1_H1_DAYTRADE:
  trigger_timeframe = H1
  H1 close_time が進んだ時だけ判定
```

state:

```text
data/results/mochipoyo/minimal_trigger_test/gold_pair_trigger_state.csv
```

### 7.1 1回目: stateなし初期化

実行:

```cmd
python scripts\apply_mochipoyo_pair_trigger_state.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --state-csv data\results\mochipoyo\minimal_trigger_test\gold_pair_trigger_state.csv --out-dir data\results\mochipoyo\minimal_trigger_test\run1 --symbol GOLD --commit-state
```

結果:

```text
pairs = 3
scan_required = 0
initialize_only = 3
skipped_no_new_bar = 0
error = 0
to_scan_rows = 0
commit_state = True
```

判定:

```text
初回は INITIALIZE_ONLY として state を保存。
scan/通知対象は0件で期待どおり。
```

保存された state:

```text
GOLD_D1_H1_DAYTRADE:
  last_seen_close_time = 2026-05-06 12:00:00

GOLD_H4_M15_DAYTRADE:
  last_seen_close_time = 2026-05-06 12:30:00

GOLD_H4_M5_SCALP:
  last_seen_close_time = 2026-05-06 12:35:00
```

### 7.2 2回目: CSV更新なし

実行:

```cmd
python scripts\apply_mochipoyo_pair_trigger_state.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --state-csv data\results\mochipoyo\minimal_trigger_test\gold_pair_trigger_state.csv --out-dir data\results\mochipoyo\minimal_trigger_test\run2 --symbol GOLD --commit-state
```

結果:

```text
pairs = 3
scan_required = 0
initialize_only = 0
skipped_no_new_bar = 3
error = 0
to_scan_rows = 0
commit_state = True
```

判定:

```text
CSV更新なしでは全GOLD pairが SKIPPED_NO_NEW_BAR。
scan/通知対象は0件で期待どおり。
```

### 7.3 3回目: GOLD_H4_M5_SCALP のstateだけ古くする

事前操作:

```cmd
python -c "import pandas as pd; p=r'data\results\mochipoyo\minimal_trigger_test\gold_pair_trigger_state.csv'; df=pd.read_csv(p,encoding='utf-8-sig'); m=df['pair_name'].astype(str).eq('GOLD_H4_M5_SCALP'); df.loc[m,'last_seen_close_time']=(pd.to_datetime(df.loc[m,'last_seen_close_time'])-pd.Timedelta(minutes=5)).dt.strftime('%Y-%m-%d %H:%M:%S'); df.to_csv(p,index=False,encoding='utf-8-sig'); print(df.to_string(index=False))"
```

変更後:

```text
GOLD_H4_M5_SCALP:
  last_seen_close_time 2026-05-06 12:35:00 -> 2026-05-06 12:30:00
```

実行:

```cmd
python scripts\apply_mochipoyo_pair_trigger_state.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --state-csv data\results\mochipoyo\minimal_trigger_test\gold_pair_trigger_state.csv --out-dir data\results\mochipoyo\minimal_trigger_test\run3 --symbol GOLD --commit-state
```

結果:

```text
pairs = 3
scan_required = 1
initialize_only = 0
skipped_no_new_bar = 2
error = 0
to_scan_rows = 1
commit_state = True
commit_scan_required = False
```

判定:

```text
GOLD_H4_M5_SCALP だけ SCAN_REQUIRED。
他2pairは SKIPPED_NO_NEW_BAR。
pair別trigger stateは期待どおり動作。
```

注意:

```text
run3では --commit-scan-required を付けていないため、GOLD_H4_M5_SCALP のstateは進めない。
これは、実運用で scan / risk / notification / ledger 処理が成功した後に last_seen_close_time を進めるための安全設計。
```

---

## 8. GOLD minimal live once 検証

実装:

```text
scripts/run_mochipoyo_gold_minimal_live_once.py
```

このスクリプトは常時ループではない。
1回分だけ以下を接続する。

```text
pair trigger state
  -> should_scan=True のGOLD pairだけscan
  -> risk enrich
  -> notification eligibility
  -> ledger duplicate filter
  -> Discord dry-run preview
  -> 成功後だけ trigger state を進める
```

### 8.1 run1

実行:

```cmd
python scripts\run_mochipoyo_gold_minimal_live_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\results\mochipoyo\minimal_live_once_test\run1 --symbol GOLD --trigger-state-csv data\results\mochipoyo\minimal_trigger_test\gold_pair_trigger_state.csv --notification-ledger-csv data\results\mochipoyo\minimal_live_once_test\gold_notification_ledger.csv --commit-trigger-state --commit-ledger --discord-dry-run --run-id gold_minimal_live_once_1
```

結果:

```text
pairs_total = 3
pairs_to_scan = 2
scan_errors = 0
notification_ok_rows = 44
ledger_new_candidates = 44
ledger_skipped_rows = 0
ledger_append_rows = 44
commit_ledger = True
discord_dry_run = True
discord_status = OK
discord_returncode = 0
commit_trigger_state = True
trigger_state_advanced = True
success = True
```

scan対象:

```text
GOLD_H4_M5_SCALP:
  previous_close_time = 2026-05-06 12:30:00
  latest_close_time   = 2026-05-06 12:50:00
  trigger_status      = SCAN_REQUIRED

GOLD_H4_M15_DAYTRADE:
  previous_close_time = 2026-05-06 12:30:00
  latest_close_time   = 2026-05-06 12:45:00
  trigger_status      = SCAN_REQUIRED
```

判定:

```text
GOLD minimal live once run1 は成功。
GOLD_H4_M5_SCALP と GOLD_H4_M15_DAYTRADE だけがscan対象になった。
notification_ok 44件が ledger新規候補になり、Discord dry-run も成功。
処理成功後に trigger state も進んだ。
```

### 8.2 run2

実行:

```cmd
python scripts\run_mochipoyo_gold_minimal_live_once.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\results\mochipoyo\minimal_live_once_test\run2 --symbol GOLD --trigger-state-csv data\results\mochipoyo\minimal_trigger_test\gold_pair_trigger_state.csv --notification-ledger-csv data\results\mochipoyo\minimal_live_once_test\gold_notification_ledger.csv --commit-trigger-state --commit-ledger --discord-dry-run --run-id gold_minimal_live_once_2
```

結果:

```text
pairs_total = 3
pairs_to_scan = 1
scan_errors = 0
notification_ok_rows = 37
ledger_new_candidates = 0
ledger_skipped_rows = 37
ledger_append_rows = 0
commit_ledger = True
discord_dry_run = True
discord_status = OK
discord_returncode = 0
commit_trigger_state = True
trigger_state_advanced = True
success = True
```

scan対象:

```text
GOLD_H4_M5_SCALP:
  previous_close_time = 2026-05-06 12:50:00
  latest_close_time   = 2026-05-06 12:55:00
  trigger_status      = SCAN_REQUIRED
```

判定:

```text
GOLD minimal live once run2 も成功。
M5 close_time が 12:50 -> 12:55 に進んだため、GOLD_H4_M5_SCALP だけがscan対象になった。
notification_ok 37件はすべて既存ledgerにより重複skip。
ledger_append_rows は0件で、重複通知防止として期待どおり。
Discord dry-run も成功。
```

---

## 9. GOLD minimal live flow 総合判定

```text
GOLD_H4_M5_SCALP:
  candidate generation PASS
  risk enrich PASS
  notification eligibility PASS
  ledger duplicate filter PASS
  Discord dry-run PASS
  pair trigger state PASS
  minimal live once PASS

GOLD_H4_M15_DAYTRADE:
  candidate generation PASS
  risk enrich PASS
  notification eligibility PASS
  ledger duplicate filter PASS
  Discord dry-run PASS
  pair trigger state PASS
  minimal live once PASS

GOLD_D1_H1_DAYTRADE:
  candidate generation PASS
  risk enrich PASS
  notification eligibility PASS
  ledger duplicate filter PASS
  Discord dry-run PASS
  pair trigger state PASS
  minimal live once PASS
```

結論:

```text
GOLD 3pair は、単発 minimal live flow まで初期PASS扱い。
まだ常時稼働ループにはしない。
次は、数回連続で run_mochipoyo_gold_minimal_live_once.py を実行し、更新がある時だけ対象pairがscanされ、ledger重複で再通知されないことを追加確認する。
```

---

## 10. 次の検証

GOLD minimal live once を追加で数回実行する。

確認項目:

```text
1. CSV更新なしなら pairs_to_scan = 0 になる
2. M5更新時は GOLD_H4_M5_SCALP だけscanされる
3. M15更新時は GOLD_H4_M15_DAYTRADE もscanされる
4. H1更新時は GOLD_D1_H1_DAYTRADE もscanされる
5. 既存payload_keyは ledger_skipped_rows に入り、ledger_new_candidates は増えない
6. success=True の時だけ trigger_state_advanced=True になる
```

常時ループ化は、この追加連続実行が安定してから行う。
