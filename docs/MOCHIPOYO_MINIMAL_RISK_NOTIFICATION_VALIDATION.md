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

## 8. 現時点の判定

```text
risk enrich:
  初期PASS相当

notification eligibility:
  初期PASS相当

minimal scanner 本体への notification eligibility 統合:
  まだ保留

本番通知:
  まだ不可
```

本番通知前に必要な残作業:

```text
1. full strict / risk enriched 側との比較
2. 最新確定足/直近数本だけの notification candidate 比較
3. ledger重複判定
4. Discord dry-run
5. pair別更新トリガーとの接続
```

---

## 9. 次の検証

次は、別CLI運用のまま full strict / risk enriched 側との比較を行う。

比較候補:

```text
minimal notification_ok CSV
vs
既存 full strict payload / allowed_events / risk enriched payload
```

比較時の注意:

```text
GOLD:
  live_risk_status == OK

BTC:
  btc_live_risk_status == OK
  spread_to_sl_ratio <= 0.07
  effective_rr_after_spread >= 1.0

payload_key:
  source_filter_name は含めない
  stable key の一致を優先
```
