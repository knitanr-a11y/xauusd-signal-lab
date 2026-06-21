# ExportGoldV3History_2023_2024.mq5 使用手順

## 出力対象

初期設定では、現在のチャートに表示しているGOLD銘柄について次を出力します。

- 期間: 2023-01-01 00:00:00 以上、2025-01-01 00:00:00 未満
- 時刻: broker server時刻
- M1 / M5 / M15 / H1 / H4 / D1
- OHLC
- tick_volume
- spread
- real_volume
- weekly trade session
- broker・server・symbol・行数などのmetadata

欠損足の補完、resample、nearest fallbackは行いません。
形成中の足も出力しません。

## MT5への入れ方

1. MT5で`F4`を押してMetaEditorを開きます。
2. MetaEditorで「ファイル」→「データフォルダを開く」を選びます。
3. `MQL5/Scripts`へ`ExportGoldV3History_2023_2024.mq5`を置きます。
4. MetaEditorでファイルを開き、`F7`でコンパイルします。
5. MT5へ戻り、ナビゲータの「スクリプト」を更新します。
6. 2026年の`goldsharp`データを取得したものと同じbroker・同じGOLD銘柄のチャートへスクリプトをドラッグします。`InpSymbol`を空欄のままにすると、そのチャートのsymbolを使用します。

## 主な入力

- `InpSymbol`
  - 空欄なら、スクリプトを置いたチャートのsymbolを使用します。
  - 例: `GOLD#`、`GOLDsharp`、`XAUUSD`
- `InpFromServer`
  - 初期値: `2023.01.01 00:00:00`
- `InpToServerExclusive`
  - 初期値: `2025.01.01 00:00:00`
  - この時刻は含みません。
- `InpFilePrefix`
  - 初期値: `gold_v3_2023_2024`
  - brokerがgoldsharpなら`goldsharp_2023_2024`などに変更可能です。
- `InpUseCommonFolder`
  - 初期値は`false`です。現在のMT5端末固有の`MQL5\Files`へ出力します。

## 出力ファイル

`InpFilePrefix=gold_v3_2023_2024`の場合:

- `gold_v3_2023_2024_m1.csv`
- `gold_v3_2023_2024_m5.csv`
- `gold_v3_2023_2024_m15.csv`
- `gold_v3_2023_2024_h1.csv`
- `gold_v3_2023_2024_h4.csv`
- `gold_v3_2023_2024_d1.csv`
- `gold_v3_2023_2024_metadata.csv`
- `gold_v3_2023_2024_weekly_sessions.csv`

出力先の絶対パスは、終了時にMT5の「エキスパート」ログへ表示されます。
初期値の`false`では、現在の端末の`MQL5\Files`へ出力します。ユーザー環境では通常、`C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\<端末ID>\MQL5\Files`です。

## 送っていただくもの

上記8ファイルをそのまま送ってください。
CSVをExcelで開いて保存し直すと、時刻・桁・区切りが変わる可能性があるため、編集せず送ってください。

## 確認点

終了ログに次が表示されます。

- `success=6/6`
- symbol名
- requested server range
- output folder

`success`が6未満の場合は、エキスパートログの`CopyRates`エラー部分も送ってください。
broker側がM1の2023年履歴を提供していない場合、スクリプト側で存在しないデータを生成することはありません。

## 安全性

このスクリプトは読取専用です。
注文送信、ポジション変更、アラート送信は行いません。
