# NEXT_CHAT_HANDOFF_BTC_AUTOTRADE_POSITION_POLICY_20260523

Last updated: 2026-05-23

BTC strict5 official 自動売買BATのポジション方針を更新した短縮引き継ぎ。

---

## 結論

TP/SLずらしは保留。

今回入れた方針:

```text
別strategy_id / 別magic_number
  -> 複数ポジション保有OK

同strategy_id / 同magic_number
  -> すでに建玉がある場合は再発注NG
```

---

## 変更済みファイル

### BTC official 自動売買BAT

```text
scripts/run_btc_strict_5_official_guarded_demo_send_forever_aligned_weekly_state.bat
```

変更後:

```text
--position-policy allow_any_until_max
--max-symbol-positions 5
--max-symbol-lot 0.05
--max-orders 5
--lot 0.01
```

旧設定:

```text
--position-policy block_any
--max-symbol-positions 1
--max-symbol-lot 0.01
--max-orders 1
```

### MT5 sender入口

```text
scripts/send_mt5_order_from_payload.py
scripts/_send_mt5_order_from_payload_original.py
```

`send_mt5_order_from_payload.py` は小さい入口になった。

`_send_mt5_order_from_payload_original.py` を読み込み、実行時に `allow_any_until_max` のポジション判定だけをメモリ上で強化する。

強化内容:

```text
allow_any_until_max:
  - 異なるmagic_numberは max-symbol-positions / max-symbol-lot の範囲で許可
  - 同じmagic_numberの既存建玉がある場合はブロック
```

ブロック時のエラー文言:

```text
position policy allow_any_until_max blocked same active magic: requested_magic=...; existing_tickets=...; existing_comments=...
```

---

## 運用上の確認ポイント

BTC自動売買BAT再起動後、sender結果で見る項目:

```text
position_policy: allow_any_until_max
max_symbol_positions: 5
max_symbol_lot: 0.05
rows_in
sent_rows
blocked_position_policy_rows
error_rows
validation_errors
```

期待挙動:

```text
別IDシグナルが複数出た場合:
  -> 最大5件まで発注候補になる

同IDのシグナルが1時間後などに再検出された場合:
  -> 既存建玉のmagic_numberと一致すれば BLOCKED_POSITION_POLICY
```

---

## 注意

```text
- TP/SL移動は未実装。保留。
- 既存BTCポジションが古いロジックのmagicなし/想定外magicの場合は同ID判定できない。
- 1ポジション0.01lot前提で、最大5ポジション=最大0.05lotにしている。
- sender本体の直接全文置換ではなく、originalを読み込む小入口方式。
```

---

## 次に見るファイル

```text
scripts/run_btc_strict_5_official_guarded_demo_send_forever_aligned_weekly_state.bat
scripts/send_mt5_order_from_payload.py
scripts/_send_mt5_order_from_payload_original.py
scripts/run_btc_strict_5_official_guarded_demo_send_forever_aligned_weekly_state.py
scripts/btc_strict_5_signals/run_btc_strict_5_official_guarded_demo_autotrade_from_csv.py
```
