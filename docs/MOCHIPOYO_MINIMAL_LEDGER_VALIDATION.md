# MOCHIPOYO Minimal Ledger Validation Log

最終更新: 2026-05-06

このドキュメントは、もちぽよ式 live notification minimal scanner の ledger重複判定とDiscord dry-run検証ログである。

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
```

この段階では Discord実送信も自動売買も行わない。

---

## 2. 実装ファイル

```text
scripts/apply_mochipoyo_notification_ledger.py
scripts/send_mochipoyo_discord_messages.py
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

## 7. GOLD ledger / Discord dry-run 総合判定

```text
GOLD_H4_M5_SCALP:
  candidate generation PASS
  risk enrich PASS
  notification eligibility PASS
  ledger duplicate filter PASS
  Discord dry-run PASS

GOLD_H4_M15_DAYTRADE:
  candidate generation PASS
  risk enrich PASS
  notification eligibility PASS
  ledger duplicate filter PASS
  Discord dry-run PASS

GOLD_D1_H1_DAYTRADE:
  candidate generation PASS
  risk enrich PASS
  notification eligibility PASS
  ledger duplicate filter PASS
  Discord dry-run PASS
```

結論:

```text
GOLD 3pair は、Discord実送信前のdry-runまで初期PASS扱い。
次は pair別更新トリガー接続へ進む。
```

---

## 8. 次の検証: GOLD pair別更新トリガー接続

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

必要なstate:

```text
last_seen_close_time_by_pair
last_scan_status_by_pair
last_notification_candidate_count_by_pair
last_ledger_append_count_by_pair
```

最低限のテスト:

```text
1回目:
  stateなし
  各GOLD pairを初期化対象として扱う
  ただし初期化モードでは送信しない
  last_seen_close_time_by_pair を保存

2回目:
  CSV更新なし
  全GOLD pair skipped_no_new_bar
  scanしない/通知しない

3回目:
  任意pairの as_of_time またはstateを調整して更新扱いにする
  対象pairだけ scan 対象になる
```

注意:

```text
run_mochipoyo_live_notify_loop.py / run_mochipoyo_live_notify_loop_light.py は本番常時稼働に使わない。
新しい minimal loop は、pair別trigger state を持つ薄い制御層として作る。
```
