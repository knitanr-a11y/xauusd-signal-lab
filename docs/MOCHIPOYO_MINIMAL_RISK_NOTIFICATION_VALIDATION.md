# MOCHIPOYO Minimal Risk / Notification Validation Log

最終更新: 2026-05-06

このドキュメントは、もちぽよ式 live notification minimal scanner の risk enrich と notification eligibility の検証ログである。

候補生成そのものの比較・tail感度は `docs/MOCHIPOYO_MINIMAL_SCANNER_VALIDATION_LOG.md` を参照する。

---

## 1. 現在の方針

risk enrich と notification eligibility は分離する。

```text
candidate generation
  -> risk enrich
  -> risk_ok
  -> notification_eligible
  -> ledger重複判定
  -> Discord送信
```

現段階では Discord送信・ledger本番統合・自動売買はまだ行わない。

---

## 2. 実装済みファイル

```text
scripts/mochipoyo_risk_enricher.py
scripts/mochipoyo_notification_filter.py
scripts/apply_mochipoyo_notification_eligibility.py
scripts/compare_mochipoyo_flexible_csvs.py
```

関連設定:

```text
scripts/mochipoyo_minimal_config.py
```

追加設定:

```text
gold_m1 -> goldsharp_m1.csv
btc_m1  -> btcusdsharp_m1.csv
pair config に touch_csv_keys を追加
BTC_H4_M15_DAYTRADE の M15 tail は 15000 以上を採用候補
```

---

## 3. Risk enrich のB案

GOLDとBTCでOK判定列を分ける。

```text
GOLD:
  live_risk_status == OK

BTC:
  btc_live_risk_status == OK
```

BTCは spread 込みのrisk判定が必須。

BTC出力必須列:

```text
current_spread_points
current_spread_price
mode_spread_points
mode_spread_price
effective_spread_price
spread_to_sl_ratio
spread_to_tp_ratio
net_sl_after_spread_price
net_tp_after_spread_price
effective_rr_after_spread
```

`btc_live_risk_status == OK` は、spread込み計算に必要な列が揃ったことを意味する。
ただし、通知適格とは別判定にする。

---

## 4. Risk enrich 実行結果

実行:

```cmd
python scripts\mochipoyo_minimal_scanner.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\results\mochipoyo\minimal_risk_enrich_test --enable-risk-enrich --tail-m15 15000
```

結果:

```text
GOLD_H4_M5_SCALP:
  normalized = 45
  risk_ok = 37
  risk_ng = 8
  touch_frames = M1,M5

GOLD_H4_M15_DAYTRADE:
  normalized = 59
  risk_ok = 7
  risk_ng = 52
  touch_frames = M5

GOLD_D1_H1_DAYTRADE:
  normalized = 24
  risk_ok = 2
  risk_ng = 22
  touch_frames = M5

BTC_H4_M15_DAYTRADE:
  normalized = 231
  risk_ok = 7
  risk_ng = 224
  touch_frames = M1,M5
```

解釈:

```text
risk enrich の接続は成功。
BTCも btc_live_risk_status == OK の候補が7件生成された。
```

---

## 5. BTC risk OK 詳細

BTC risk OK 7件は、spread列がすべて揃っていた。

```text
rows = 7
risk_status = OK
btc_live_risk_status = OK
current_spread_points = 2250
current_spread_price = 22.5
mode_spread_points = 2250
mode_spread_price = 22.5
effective_spread_price = 22.5
spread_to_sl_ratio = finite
effective_rr_after_spread = finite
net_sl_after_spread_price = finite
net_tp_after_spread_price = finite
```

BTC risk OK 7件のうち、spread込み実効RRが低いものがある。

除外候補例:

```text
2026-04-28 04:00 SELL:
  spread_to_sl_ratio = 0.223436
  effective_rr_after_spread = 0.798214

2026-05-02 00:00 BUY:
  spread_to_sl_ratio = 0.180578
  effective_rr_after_spread = 0.863494

2026-05-02 16:00 BUY:
  spread_to_sl_ratio = 0.119300
  effective_rr_after_spread = 0.965514
```

したがって、BTCでは `btc_live_risk_status == OK` だけでは通知候補にしない。

---

## 6. Notification eligibility 仕様

通知適格判定は risk OK より厳しい。

```text
GOLD:
  live_risk_status == OK

BTC:
  btc_live_risk_status == OK
  spread_to_sl_ratio <= 0.07
  effective_rr_after_spread >= 1.0
```

この判定は以下の後処理CLIで実行する。

```text
scripts/apply_mochipoyo_notification_eligibility.py
```

現段階では minimal scanner 本体への統合は保留。
まず別CLIで full strict / risk enriched 側との比較を続ける。

---

## 7. Notification eligibility 実行結果

実行:

```cmd
python scripts\apply_mochipoyo_notification_eligibility.py --input-dir data\results\mochipoyo\minimal_risk_enrich_test --out-dir data\results\mochipoyo\minimal_notification_filter_test --risk-ok-only
```

結果:

```text
BTC_H4_M15_DAYTRADE:
  risk_ok = 7
  notification_ok = 4
  notification_ng = 3

GOLD_D1_H1_DAYTRADE:
  risk_ok = 2
  notification_ok = 2
  notification_ng = 0

GOLD_H4_M15_DAYTRADE:
  risk_ok = 7
  notification_ok = 7
  notification_ng = 0

GOLD_H4_M5_SCALP:
  risk_ok = 37
  notification_ok = 37
  notification_ng = 0
```

BTC notification OK 4件:

```text
2026-04-28 20:00 SELL
  spread_to_sl_ratio = 0.030447
  effective_rr_after_spread = 1.134997

2026-05-03 16:00 BUY
  spread_to_sl_ratio = 0.033044
  effective_rr_after_spread = 1.129628

2026-05-04 00:00 BUY
  spread_to_sl_ratio = 0.062043
  effective_rr_after_spread = 1.071479

2026-05-05 21:00 BUY
  spread_to_sl_ratio = 0.030078
  effective_rr_after_spread = 1.135760
```

判定:

```text
notification eligibility は期待どおり動作。
BTC risk_ok 7件から、spread条件と実効RR条件により4件へ絞り込み。
GOLDは risk_ok がそのまま notification_ok になる。
```

---

## 8. Full strict allowed_events vs minimal notification_ok 比較

比較には、正規化済み/enriched済みCSVを再正規化せず扱える以下を使用する。

```text
scripts/compare_mochipoyo_flexible_csvs.py
```

比較の主目的:

```text
minimal notification_ok が full strict allowed_events 側に存在するか確認する。

重視:
  matched_rows
  minimal_only_rows
  payload_key_diff_rows

参考扱い:
  full_only_rows
  value_diff_rows
```

理由:

```text
full strict allowed_events は risk/notification 前の母集団に近い。
そのため full_only_rows は残り得る。
また full側にrisk/SL/TP/spread列が無い場合、value_diff_rows は大きく出る。
```

---

## 9. GOLD notification comparison 結果

### 9.1 GOLD_H4_M5_SCALP

実行:

```cmd
python scripts\compare_mochipoyo_flexible_csvs.py --full-csv data\results\mochipoyo\live_dryrun\gold_mochipoyo_live_dryrun_strict_allowed_events.csv --minimal-csv data\results\mochipoyo\minimal_notification_filter_test\minimal_candidates_notification_ok_gold_h4_m5_scalp.csv --pair-name GOLD_H4_M5_SCALP --align-both-to-overlap-time-range --out-dir data\results\mochipoyo\flex_compare_gold_h4_m5_notification_ok_vs_allowed_events --lookback-candidates 0
```

結果:

```text
full_rows = 38
minimal_rows = 37
matched_rows = 37
full_only_rows = 1
minimal_only_rows = 0
payload_key_diff_rows = 0
```

full_only 1件:

```text
GOLD_H4_M5_SCALP A SELL
signal_close_time = 2026-05-02 00:00:00
entry_time        = 2026-05-04 01:00:00
entry_price       = 4632.78
risk_status       = NaN
```

解釈:

```text
minimal notification_ok 37件は、full strict allowed_events 側に全件存在。
full_only 1件は signal_close_time と entry_time が約2日ズレており、通知候補として除外されるのは自然。
```

判定:

```text
GOLD_H4_M5_SCALP notification candidate generation: PASS扱い
```

### 9.2 GOLD_H4_M15_DAYTRADE

実行:

```cmd
python scripts\compare_mochipoyo_flexible_csvs.py --full-csv data\results\mochipoyo\live_dryrun\gold_mochipoyo_live_dryrun_strict_allowed_events.csv --minimal-csv data\results\mochipoyo\minimal_notification_filter_test\minimal_candidates_notification_ok_gold_h4_m15_daytrade.csv --pair-name GOLD_H4_M15_DAYTRADE --align-both-to-overlap-time-range --out-dir data\results\mochipoyo\flex_compare_gold_h4_m15_notification_ok_vs_allowed_events --lookback-candidates 0
```

結果:

```text
full_rows = 9
minimal_rows = 7
matched_rows = 7
full_only_rows = 2
minimal_only_rows = 0
payload_key_diff_rows = 0
```

解釈:

```text
minimal notification_ok 7件は、full strict allowed_events 側に全件存在。
full_only 2件は full側のrisk/notification前候補として扱う。
```

判定:

```text
GOLD_H4_M15_DAYTRADE notification candidate generation: PASS扱い
```

### 9.3 GOLD_D1_H1_DAYTRADE

実行:

```cmd
python scripts\compare_mochipoyo_flexible_csvs.py --full-csv data\results\mochipoyo\live_dryrun\gold_mochipoyo_live_dryrun_strict_allowed_events.csv --minimal-csv data\results\mochipoyo\minimal_notification_filter_test\minimal_candidates_notification_ok_gold_d1_h1_daytrade.csv --pair-name GOLD_D1_H1_DAYTRADE --align-both-to-overlap-time-range --out-dir data\results\mochipoyo\flex_compare_gold_d1_h1_notification_ok_vs_allowed_events --lookback-candidates 0
```

結果:

```text
full_rows = 2
minimal_rows = 2
matched_rows = 2
full_only_rows = 0
minimal_only_rows = 0
payload_key_diff_rows = 0
```

解釈:

```text
minimal notification_ok 2件は、full strict allowed_events 側と完全一致。
```

判定:

```text
GOLD_D1_H1_DAYTRADE notification candidate generation: PASS扱い
```

### 9.4 GOLD 3pair 総合判定

```text
GOLD_H4_M5_SCALP:
  matched 37 / minimal_only 0 / payload_key_diff 0

GOLD_H4_M15_DAYTRADE:
  matched 7 / minimal_only 0 / payload_key_diff 0

GOLD_D1_H1_DAYTRADE:
  matched 2 / minimal_only 0 / payload_key_diff 0
```

結論:

```text
GOLD 3pair は、candidate generation / risk enrich / notification eligibility まで初期PASS扱い。
次は GOLD だけ先に ledger重複判定へ進めてよい。
```

---

## 10. BTC notification comparison 結果

比較:

```cmd
python scripts\compare_mochipoyo_flexible_csvs.py --full-csv data\results\mochipoyo\live_dryrun\btc_mochipoyo_live_dryrun_strict_allowed_events.csv --minimal-csv data\results\mochipoyo\minimal_notification_filter_test\minimal_candidates_notification_ok_btc_h4_m15_daytrade.csv --pair-name BTC_H4_M15_DAYTRADE --align-both-to-overlap-time-range --out-dir data\results\mochipoyo\flex_compare_btc_notification_ok_vs_allowed_events --lookback-candidates 0
```

結果:

```text
full_rows = 4
minimal_rows = 4
matched_rows = 2
full_only_rows = 2
minimal_only_rows = 2
payload_key_diff_rows = 0
```

full_only:

```text
2026-05-02 10:45 BUY
2026-05-03 18:45 BUY
```

minimal_only:

```text
2026-05-03 16:00 BUY
2026-05-04 00:00 BUY
```

解釈:

```text
BTCは payload_key ルールの問題ではなく、候補時刻そのものがズレている。
これまでのtail感度でも見えていた通り、tail/warmup/cooldown/pivot初期化影響がGOLDより強い。
```

判定:

```text
BTC risk/spread enrich: 動作OK
BTC notification eligibility: 動作OK
BTC notification candidate generation: 未PASS
```

BTCの次工程:

```text
full期間全体ではなく、最新確定足/直近数本だけで比較する設計に切り替える。
```

---

## 11. 現時点の判定

```text
GOLD_H4_M5_SCALP:
  candidate generation PASS
  risk enrich PASS
  notification eligibility PASS

GOLD_H4_M15_DAYTRADE:
  candidate generation PASS
  risk enrich PASS
  notification eligibility PASS

GOLD_D1_H1_DAYTRADE:
  candidate generation PASS
  risk enrich PASS
  notification eligibility PASS

BTC_H4_M15_DAYTRADE:
  candidate generation 動作OK。ただし候補時刻一致は未PASS
  risk/spread enrich PASS
  notification eligibility PASS
```

本番通知前に必要な残作業:

```text
1. GOLD ledger重複判定
2. GOLD Discord dry-run
3. GOLD pair別更新トリガー接続
4. BTC 最新確定足/直近数本限定比較
5. BTC ledger/DiscordはBTC候補時刻比較が通ってから
```

---

## 12. 次の検証

GOLDだけ先に ledger重複判定へ進む。

必要状態:

```text
payload_key
last_notified_time_by_symbol_pair_direction
send ledger
```

最低限のテスト:

```text
1回目:
  notification_ok CSV を入力
  payload_key未送信なら送信候補として残る

2回目:
  同じCSVを入力
  sent 0 / duplicate skip

同一payload_keyが複数CSV/複数フィルターに存在しても:
  1回だけ通知候補
```
