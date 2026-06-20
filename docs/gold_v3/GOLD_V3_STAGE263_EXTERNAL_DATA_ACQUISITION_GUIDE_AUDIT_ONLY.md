# GOLD V3 Stage263 外部データ取得ガイド

状態: `GOLD_V3_263_EXTERNAL_DATA_ACQUISITION_SCAFFOLD_AUDIT_ONLY`

## 目的

Stage262で不足した事前calendarと方向情報を収集する。候補探索・発注は行わない。

## 1. broker metadata

最初に記録する。

- broker company
- MT5 server name
- actual symbol name
- server timezone
- digits
- contract description
- account種別

ログイン番号、パスワード、API secretは保存しない。

## 2. tick export

`scripts/gold_v3/stage263_export_mt5_ticks.py`を、MT5 terminalが起動・ログイン済みのWindows環境で実行する。

例:

```powershell
python scripts/gold_v3/stage263_export_mt5_ticks.py `
  --symbol "ACTUAL_GOLD_SYMBOL" `
  --from-utc "2025-01-01T00:00:00Z" `
  --to-utc "2026-06-20T00:00:00Z" `
  --out "data/gold_ticks_2025_2026.csv"
```

このscriptはread-onlyで、order/position APIを呼ばない。

出力:

- time_msc / time_utc
- bid / ask / last
- flags
- raw volume fields
- broker/server ID
- terminal build / package version metadata

MT5が保持していない過去tickは取得できない。その場合は、現在以降のlive tick recorder期間を新しい未見holdoutとして蓄積する。

## 3. current weekly sessions

`ExportGoldWeeklySessions.mq5`をMT5 Scriptsへ置き、対象symbolのチャート上で実行する。

これは`SymbolInfoSessionTrade`が返す現在の曜日別sessionを記録するだけで、過去・将来のholiday/short-session exceptionsは含まない。

したがって、次のofficial broker資料を別に保存する。

- 2025 holiday trading hours
- 2026 holiday trading hours
- short-session notices
- notice publication timestamp
- broker/server/symbol適用範囲

## 4. external synchronized data

最低限:

- DXYまたはUSD index
- US 2-year yield
- US 10-year yield
- COMEX GC futures

必須列:

- source_name
- symbol
- time_utc
- source_available_at
- OHLCまたはtick値
- source_version

後から改定された値を、当時利用可能だった値として扱わない。

## 5. macro calendar

必須列:

- event_id / event_name
- scheduled_time_utc
- importance
- country / currency
- published_at
- source/version

actual、forecast、surpriseはentry前情報として使用しない。まずscheduled timeによるno-trade/context監査だけを行う。

## 6. data validation

`scripts/gold_v3/stage262_data_contracts.py`でschemaを検証する。

入力template:

- broker session calendar
- tick data
- external market data
- macro calendar
- broker metadata

## 7. 継続条件

次を満たすまで候補探索へ戻らない。

1. pre-known broker calendarが全candidate sessionをcover。
2. Stage262 exit batch/live/restart parityが全candidateでPASS。
3. tick dataにtime_msc、bid、askが存在。
4. external dataのavailability-time契約が確認済み。
5. 新仮説は最大2種類を結果前に固定。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
