# BTC AI研究用 MT5履歴CSVエクスポーター

日付: 2026-08-03

## 目的

MetaTrader 5のブローカー履歴から、BTC AI研究用の確定足CSVを取得する。

対象時間足:

- M1
- M5
- M15
- H1
- H4
- D1

既定取得開始:

`2023.01.01 00:00:00`

既定取得終了:

実行時点の最新確定足。

時刻は変換せず、MT5 broker-server naive timeをそのまま出力する。形成中の足は出力しない。

## 出力列

```text
time;open;high;low;close;tick_volume;spread;real_volume
```

GOLD研究で使用したCSVと同じ基本列とする。

## スクリプト

`mt5/btc_ai_v1/BTC_AI_History_Exporter.mq5`

## MT5への配置

1. MT5を起動する。
2. `ファイル` → `データフォルダを開く`。
3. `MQL5` → `Scripts`を開く。
4. `BTC_AI_History_Exporter.mq5`をコピーする。
5. MetaEditorで開いてコンパイルする。
6. MT5のナビゲータで`スクリプト`を右クリックし、`更新`する。

## 実行前の設定

MT5の次を十分大きくする。

`ツール` → `オプション` → `チャート` → `チャートの最大バー数`

M1は数百万行になる可能性があるため、可能なら最大値にする。

対象BTC銘柄を気配値表示へ追加する。ブローカーによりsymbol名が異なる。

例:

- `BTCUSD`
- `BTCUSD.a`
- `BTCUSD#`
- `BTCUSDm`

## 実行方法

1. 対象BTCチャートを開く。
2. ナビゲータの`BTC_AI_History_Exporter`をチャートへドラッグする。
3. 入力値を確認して実行する。

主要入力:

- `InpSymbol`
  - 空欄ならスクリプトを置いたチャートの銘柄を使う。
  - 別名を明示する場合はブローカーの正確なsymbol名を入力する。
- `InpStartTime`
  - 既定は`2023.01.01 00:00:00`。
- `InpEndTime`
  - `0`なら最新確定足まで。
- `InpOutputFolder`
  - 既定は`BTC_AI_RESEARCH_DATA`。
- `InpChunkDays`
  - M1を一括取得せず分割する日数。通常は31のまま。

## 保存場所

既定:

```text
MT5データフォルダ\MQL5\Files\BTC_AI_RESEARCH_DATA\
```

生成例:

```text
BTCUSD_M1_20230101_20260803.csv
BTCUSD_M5_20230101_20260803.csv
BTCUSD_M15_20230101_20260803.csv
BTCUSD_H1_20230101_20260803.csv
BTCUSD_H4_20230101_20260803.csv
BTCUSD_D1_20230101_20260803.csv
export_manifest.csv
symbol_metadata.csv
```

## 完成判定

各時間足は一度`.part`へ書かれ、最後まで成功した場合だけ`.csv`へrenameされる。

`.part`が残っている場合、その時間足は未完了として扱う。

`export_manifest.csv`には次を記録する。

- 実取得開始・終了時刻
- 行数
- gap数
- 最大gap秒数
- spread pointsの最小・最大
- 成功・失敗status

`symbol_metadata.csv`には次を記録する。

- broker会社・account server
- symbol名・description
- digits・point
- tick size・tick value・contract size
- base/profit/margin currency
- 取得時刻契約

## 取得後の監査

出力フォルダ全体をZIPで共有し、研究開始前に次を監査する。

- 2023年からの履歴が実在するか
- timestamp重複・逆順
- M1/M5/M15/H1/H4/D1のOHLC整合性
- broker-server時刻
- 週末・メンテナンスgap
- spread pointsの単位と異常値
- 2023～2026年の期間別欠損
- 複数broker sourceの結合可否

ブローカー側に2023年のBTC履歴が存在しない場合、スクリプトだけで生成することはできない。その場合、manifestの`actual_first`は2023年より後になる。

## 現在の境界

- 旧BTC BCR研究は新AI研究の再開authorityにしない。
- GOLDのV19、Challenger C1、P75を変更しない。
- CSV監査完了前に候補探索を始めない。
- MT5 order、Discord、live-ready、final signalは作らない。
