# NEXT CHAT HANDOFF - MOCHIPOYO MINIMAL LIVE

最終更新: 2026-05-06

このドキュメントは、次チャットで `もちぽよ式 GOLD minimal live dry loop` の続きから始めるための引き継ぎである。

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
```

BTCを触る場合は以下も読む。

```text
docs/IMPORTANT_BTC_SPREAD_REVALIDATION.md
```

---

## 2. 現在の到達点

GOLD 3pair のもちぽよ式 minimal live flow は、Discord実送信なしの dry loop までPASS扱い。

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
GOLD Discord dry-run / no-row skip: PASS
GOLD pair trigger state: PASS
GOLD minimal live once stability: PASS
GOLD minimal live dry loop: PASS
```

まだDiscord実送信はしていない。
自動売買もしていない。

---

## 3. 追加・修正済みファイル

今回の主な追加/修正ファイル:

```text
scripts/apply_mochipoyo_pair_trigger_state.py
scripts/run_mochipoyo_gold_minimal_live_once.py
scripts/run_mochipoyo_gold_minimal_live_loop_dry.py
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

重要コミット:

```text
d04e49d315e324add95a2c5e3af157dc85ef27ef
  Add pair trigger state validator for minimal loop

13139fb291753eef0ec592973225af7065700c3c
  Add one-shot GOLD minimal live flow orchestrator

0d897117218590ab8861c8f0554d6dfbc0320bac
  Filter live once notifications to trigger window

7c2fa1e5081997ef042f76eb8d32628edcec13b1
  Skip Discord dry-run when no rows to send

023c0e6507838b530715817f1a4b0c9397bde0e6
  Add dry loop wrapper for GOLD minimal live once

566e321e541fc4c9b364f96c203bc7ca14f7f831
  Precreate iteration output subdirectories in dry loop

b3cdaa6dca64ef7c7bfa4027a10b32d941f99392
  Support Windows long paths in minimal live once CSV writes

fb689df21faee997192d51094998619e18b78178
  Document GOLD dry loop validation and long path fix
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

検証済み:

```text
初回 stateなし:
  INITIALIZE_ONLY = 3
  to_scan_rows = 0

CSV更新なし:
  SKIPPED_NO_NEW_BAR = 3
  to_scan_rows = 0

1pairだけstateを古くする:
  対象pairだけ SCAN_REQUIRED
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

実際にrun3で見つかった問題:

```text
GOLD_D1_H1_DAYTRADE を初めてscanした時、
2026-04-15 / 2026-04-16 の過去候補2件が
ledger未登録の新規候補として出た。
```

対策済み:

```text
trigger更新窓外の候補は notification_outside_trigger_window へ落とす。
ledgerにもDiscordにも流さない。
```

---

## 6. Discord dry-run / no-row skip の仕様

Discord実送信はまだ行わない。
`run_mochipoyo_gold_minimal_live_loop_dry.py` は常に one-shot を `--discord-dry-run` で呼ぶ。

送信候補0件の場合:

```text
discord_status = SKIPPED_NO_ROWS
discord_returncode = 0
success = True
```

空CSVをDiscord送信スクリプトへ渡してERRORにしない。

---

## 7. Windows long path 対応

MT5のMQL5/Files配下はパスが長く、dry loopの深い出力先では `pandas.to_csv()` が `FileNotFoundError` になることがあった。

発生例:

```text
FileNotFoundError:
...\iter_0001\notification\minimal_candidates_notification_outside_trigger_window_gold_h4_m5_scalp.csv
```

対応済み:

```text
run_mochipoyo_gold_minimal_live_once.py:
  Windowsでは CSV保存時に \\?\ 付き extended-length path を使う

run_mochipoyo_gold_minimal_live_loop_dry.py:
  iteration開始時に scan/notification/ledger/discord を事前作成
```

さらに検証時は短いout-dirを使う。

推奨:

```text
data/ml_loop_runX
```

避けたい長いout-dir:

```text
data/results/mochipoyo/minimal_live_loop_dry_test/runX
```

---

## 8. 直近の成功検証: dry loop run4

実行コマンド:

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
dry loop wrapper: PASS
once呼び出し: PASS
Windows long path対応: PASS
pair trigger state更新: PASS
更新なしskip: PASS
trigger window filter: PASS
Discord no-row skip: PASS
```

---

## 9. 次チャットでやること: A案 長めのdry loop

ユーザー希望は A案。

目的:

```text
iterations = 12
sleep_seconds = 10〜30
```

で、M5/M15/H1更新タイミングをまたいでも安定して動くか確認する。

推奨コマンド:

```cmd
python scripts\run_mochipoyo_gold_minimal_live_loop_dry.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\ml_loop_run5 --symbol GOLD --trigger-state-csv data\results\mochipoyo\minimal_trigger_test\gold_pair_trigger_state.csv --notification-ledger-csv data\results\mochipoyo\minimal_live_once_test\gold_notification_ledger.csv --iterations 12 --sleep-seconds 15 --commit-trigger-state --commit-ledger
```

確認コマンド:

```cmd
python -c "import pandas as pd; p=r'data\ml_loop_run5\gold_minimal_live_loop_dry_summary.csv'; df=pd.read_csv(p,encoding='utf-8-sig'); cols=[c for c in ['loop_iteration','returncode','pairs_to_scan','notification_ok_live_rows','notification_outside_trigger_window_rows','ledger_new_candidates','ledger_append_rows','discord_status','success'] if c in df.columns]; print(df[cols].to_string(index=False))"
```

成功条件:

```text
全iteration returncode = 0
全iteration success = True
Discord実送信なし
自動売買なし
pairs_to_scan は更新タイミングに応じて 0/1/2/3 で自然に変動
trigger更新窓外の候補は notification_outside_trigger_window に落ちる
ledger_new_candidates は live window 内の新規payload_keyがある時だけ増える
送信候補0件なら discord_status = SKIPPED_NO_ROWS
```

---

## 10. 次チャットでやってはいけないこと

```text
- Discord実送信へすぐ進む
- 自動売買を入れる
- 既存の run_mochipoyo_live_notify_loop.py / run_mochipoyo_live_notify_loop_light.py を使う
- trigger更新窓フィルターを無効化する
- 長い out-dir を使ってWindows path問題を再発させる
- notification_outside_trigger_window を通知候補として扱う
- ledger_new_candidates が0だから異常と判断する
```

---

## 11. 次の判断基準

長めdry loopが安定した後の次候補:

```text
1. Discord本文preview確認
2. 実Discord送信の1件dry-to-live切替テスト
3. BTC minimal flowへ進む前のBTC spread再確認
```

まだ実送信前なので、次チャットではまず A案の長めdry loopを完了させる。
