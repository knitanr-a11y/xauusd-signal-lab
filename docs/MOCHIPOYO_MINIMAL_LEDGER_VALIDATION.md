# MOCHIPOYO Minimal Ledger Validation Log

最終更新: 2026-05-06

このドキュメントは、もちぽよ式 live notification minimal scanner の ledger重複判定検証ログである。

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
```

この段階では Discord送信も自動売買も行わない。

---

## 2. 実装ファイル

```text
scripts/apply_mochipoyo_notification_ledger.py
```

役割:

```text
notification_ok CSV を入力
既存 ledger CSV を読む
payload_key を判定
NEW / DUPLICATE_EXISTING / DUPLICATE_IN_INPUT_BATCH / NOT_NOTIFICATION_ELIGIBLE / INVALID_PAYLOAD_KEY を分類
必要なら --commit-ledger で ledger CSV に追記
state CSV を出力
```

出力:

```text
notification_ledger_classified.csv
notification_ledger_to_send.csv
notification_ledger_skipped.csv
notification_ledger_append_preview.csv
notification_ledger_state.csv
notification_ledger_summary.csv
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

## 4. 1回目実行

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

## 5. 2回目実行

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

## 6. GOLD ledger重複判定 総合判定

```text
GOLD_H4_M5_SCALP:
  candidate generation PASS
  risk enrich PASS
  notification eligibility PASS
  ledger duplicate filter PASS

GOLD_H4_M15_DAYTRADE:
  candidate generation PASS
  risk enrich PASS
  notification eligibility PASS
  ledger duplicate filter PASS

GOLD_D1_H1_DAYTRADE:
  candidate generation PASS
  risk enrich PASS
  notification eligibility PASS
  ledger duplicate filter PASS
```

結論:

```text
GOLD 3pair は、Discord送信前の ledger重複判定まで初期PASS扱い。
次は Discord dry-run に進める。
```

---

## 7. 次の検証

Discord送信はまだ行わず、既存の送信スクリプトを dry-run で使う。

候補入力:

```text
data/results/mochipoyo/minimal_ledger_test/run1/notification_ledger_to_send.csv
```

注意:

```text
run2/notification_ledger_to_send.csv は0件のため、dry-run対象はrun1側を使う。
実運用では ledger判定後の notification_ledger_to_send.csv だけを送信スクリプトへ渡す。
```

次の確認項目:

```text
1. 送信候補46件を読み込めるか
2. payload_keyを保持したままDiscord previewを作れるか
3. preview_txt / preview_json が生成されるか
4. --send を付けない限りDiscordへ送信されないか
```
