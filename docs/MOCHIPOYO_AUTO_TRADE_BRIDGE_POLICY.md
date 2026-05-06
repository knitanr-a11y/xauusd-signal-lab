# MOCHIPOYO Auto-Trade Bridge Policy

最終更新: 2026-05-06

このドキュメントは、もちぽよ式 GOLD/BTC 通知システムを将来自動売買へ進める場合の MQL5 EA / Python 連携方針である。

重要: 現時点では自動売買を実装しない。まず live notification minimal scanner を完成させ、full strict scan vs minimal scan 一致検証、tail本数感度テスト、pair別更新トリガーテスト、重複通知テストを通す。

---

## 1. 結論

EAが1つしか使えない前提では、将来はローソク足Export EAと自動売買EAを分けない。

最終形は、1つのMQL5 Bridge EAに以下を統合する。

```text
MochipoyoBridgeEA.mq5
  - OHLC CSV Export
  - Python order_intent reader
  - MT5 trade executor
  - position manager
  - execution report writer
```

PythonはMT5へ直接発注しない。
Pythonはシグナル判定後、必要な場合だけ order_intent ファイルを出す。
EAがその order_intent を読み、MT5上で発注・拒否・結果記録を行う。

---

## 2. 役割分担

### 2.1 MQL5 Bridge EA

```text
- GOLD/BTC 各timeframeの確定足をCSVへ出力する
- Pythonが作成した order_intent を読む
- MT5で発注/決済/SL/TP設定を行う
- 約定/拒否/エラー/ポジション状態を execution_report へ書く
```

EAは `InpIncludeCurrentBar=false` を維持し、形成中足ではなく確定足のみをCSVへ出す。

### 2.2 Python

```text
- MQL5/Files のOHLC CSVを読む
- live notification minimal scannerでシグナル判定する
- risk_status OK の候補だけDiscord通知候補にする
- 自動売買ONかつ auto_trade_eligible true の場合だけ order_intent を出す
- EAが返した execution_report を読み、ledger/auditへ記録する
```

---

## 3. 通知OKと自動売買OKは分ける

通知条件と発注条件を同一にしない。

```text
risk_status == OK
  -> Discord通知は可能

auto_trade_eligible == true
  -> 自動売買発注可能
```

BTCでは特に、自動売買条件を通知より厳しくする。

```text
spread取得不能 -> auto_trade_eligible false
spread_to_sl_ratio 上限超え -> auto_trade_eligible false
effective_rr_after_spread 下限未満 -> auto_trade_eligible false
```

---

## 4. Python -> EA: order_intent

Pythonは将来、自動売買ONのときだけ order_intent を出す。

保存先案:

```text
MQL5/Files/mochipoyo_order_intents/pending/order_<order_intent_id>.json
```

最小フィールド案:

```json
{
  "order_intent_id": "abc123",
  "payload_key": "GOLD|GOLD_H4_M15_DAYTRADE|B|SELL|2026-05-06 10:15:00|2026-05-06 10:15:00|4675.20",
  "symbol": "GOLD",
  "mt5_symbol": "GOLD#",
  "pair_name": "GOLD_H4_M15_DAYTRADE",
  "candidate_rank": "B",
  "direction": "SELL",
  "entry_type": "MARKET",
  "entry_time": "2026-05-06 10:15:00",
  "entry_price": 4675.20,
  "sl_price": 4683.20,
  "tp_price": 4663.20,
  "risk_status": "OK",
  "auto_trade_eligible": true,
  "created_at": "2026-05-06 10:15:05"
}
```

`order_intent_id` は `payload_key` から作る短いハッシュを基本候補とする。

---

## 5. EA -> Python: execution_report

EAは order_intent の処理結果をCSVへ返す。

保存先案:

```text
MQL5/Files/mochipoyo_execution_reports/executions_YYYYMM.csv
```

列案:

```text
reported_at
order_intent_id
payload_key
symbol
mt5_symbol
pair_name
candidate_rank
direction
request_status
retcode
retcode_description
deal_ticket
order_ticket
filled_price
sl_price
tp_price
volume
reject_reason
position_ticket
```

---

## 6. pair configへの影響

minimal scannerのpair configには、将来自動売買用に以下のフィールドを持たせる。

```text
mt5_symbol
auto_trade_enabled
```

ただし現時点では全pairで以下を固定する。

```text
auto_trade_enabled = false
```

理由:

```text
- 今は通知システムと検証基盤を作る段階
- 自動売買はfull/minimal一致検証後に設計する
- 誤発注を防ぐため、初期値は必ずfalse
```

現在の初期値:

```text
GOLD pairs -> mt5_symbol = GOLD#
BTC pairs  -> mt5_symbol = BTCUSD#
```

ブローカーや口座で実symbolが違う場合は、pair config側で変更する。

---

## 7. payload_keyとorder_intent_id

payload_keyは通知・重複防止の安定キー。

```text
symbol|pair_name|candidate_rank|direction|signal_close_time|entry_time|entry_price_normalized
```

order_intent_idは発注指示の一意ID。

```text
order_intent_id = hash(payload_key)
```

payload_keyは長くてもよいが、ファイル名・EA処理・ログでは短いorder_intent_idを併用する。

---

## 8. 現時点で作らないもの

```text
- order_intent writer
- execution_report reader
- MQL5 Bridge EA
- 自動売買発注ロジック
- ポジション管理ロジック
- AI評価との再接続
```

これらは、live notification minimal scanner が以下を通してから作る。

```text
1. full strict scan vs minimal scan PASS
2. tail本数感度テスト PASS
3. pair別更新トリガーテスト PASS
4. 重複通知テスト PASS
5. Discord通知再確認 PASS
```

---

## 9. 現在のminimal scanner設計への結論

大きな仕様変更は不要。

ただし、将来自動売買に備えて以下を仕様に含める。

```text
- pair configに mt5_symbol を持つ
- pair configに auto_trade_enabled を持つ
- 通知判定と自動売買判定を分ける
- Pythonは直接発注せず order_intent を出す
- EAは execution_report を返す
- 最終的なEAは OHLC Export + Trade Bridge 一体型にする
```
