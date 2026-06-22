# ExportGoldV3ForwardTickWindow.mq5 使用手順

## 結論

このツールはEAではなく、1回実行型のMQL5 **スクリプト**です。

現在稼働しているローソク足取得EAを外しません。EA枠も使用しません。

GitHub上の配置:

- スクリプト: `tools/mt5/ExportGoldV3ForwardTickWindow.mq5`
- この手順書: `docs/gold_v3/README_EXPORT_GOLD_V3_FORWARD_TICK_WINDOW_MT5_JA.md`

MT5側の配置:

- `MQL5/Scripts/ExportGoldV3ForwardTickWindow.mq5`

出力先:

- 初期設定では、現在のMT5端末固有の `MQL5/Files` 直下
- `InpUseCommonFolder=true` の場合だけ共通Files

既存の `tools/mt5/ExportGoldV3History_2023_2024.mq5` と同じ配置・出力方針です。新しい保存先を推測して作っていません。

## なぜ過去tick一括取得を作り直さないのか

Stage273の正式監査で、現在のXMTrading-MT5 3 / `GOLD#`について次が確認済みです。

- 2023年: 0 tick
- 2024年: 0 tick
- 2025年: 0 tick
- 2026年: 10,146,463 tick
- 最初の取得可能tick: `2026-05-13 01:00:02.024`

ブローカーがこの端末へ古いtick履歴を提供していないため、別スクリプトを作っても2023～2025年のtickを生成することはできません。

Stage273の正式方針どおり、今後必要な候補時刻の前後だけを狭い範囲で出力します。

## 安全契約

- GOLD V3 audit-only
- 注文送信なし
- ポジション変更なし
- 決済なし
- Discord通知なし
- AI APIなし
- final signalなし
- 現在のローソク足取得EAは変更しない
- 欠損tickの生成・補間・nearest fallbackなし
- JST変換なし
- 入力範囲はbroker server時刻
- `time_msc`はMT5が返した生値を保存

## MT5への導入

1. GitHub DesktopまたはVS CodeでリポジトリをPullします。
2. MT5で`F4`を押してMetaEditorを開きます。
3. MetaEditorで「ファイル」→「データフォルダを開く」を選びます。
4. `MQL5/Scripts`を開きます。
5. リポジトリの次のファイルをコピーします。

   `tools/mt5/ExportGoldV3ForwardTickWindow.mq5`

6. MetaEditorで開き、`F7`でコンパイルします。
7. MT5へ戻り、ナビゲータの「スクリプト」を更新します。
8. 現在使用しているものと同じbroker・同じGOLD銘柄のチャートへドラッグします。

これはスクリプトなので、実行が終わると自動的にチャートから外れます。現在のEAはそのまま残ります。

## 最初の確認方法

初期値のまま実行してください。

- `InpRangeMode = GOLD_V3_LAST_HOURS`
- `InpLastHours = 1`
- `InpSymbol = 空欄`

空欄の場合、スクリプトを置いたチャートの銘柄を使います。`GOLD#`チャートへ置いてください。

直近1時間のtickを取得します。

出力例:

- `gold_v3_forward_tick_window_GOLD__20260622_120000_20260622_130000.csv`
- `gold_v3_forward_tick_window_GOLD__20260622_120000_20260622_130000_metadata.csv`

`#`はファイル名で`_`へ置換されます。

## 候補時刻の前後だけ取得する方法

`InpRangeMode`を次へ変更します。

`GOLD_V3_EXPLICIT_SERVER_RANGE`

その上で、候補時刻の前後をbroker server時刻で設定します。

例として候補時刻が `2026.06.22 13:15:00` の場合:

- `InpFromServer = 2026.06.22 13:12:00`
- `InpToServerExclusive = 2026.06.22 13:18:00`

終了時刻は含まない半開区間です。

## 出力CSV

tick CSVの列:

- `tick_time_text`
- `tick_time_epoch_seconds`
- `time_msc_raw`
- `bid`
- `ask`
- `last`
- `volume`
- `volume_real`
- `flags`
- `spread_price`

metadata CSVの主な項目:

- broker会社
- account server
- terminal build
- symbol
- digits / point
- 要求した開始・終了server時刻
- tick件数
- 最初・最後の`time_msc`
- 空だったchunk数
- CopyTicksRangeエラー数
- status

status:

- `SUCCESS`: tickを1件以上取得
- `NO_TICKS_RETURNED`: 呼出しは成功したが、その期間のtickが0件
- `PARTIAL_COPY_ERRORS`: 一部chunkで取得エラー
- `COPY_FAILED`: 全件0で取得エラーあり

`NO_TICKS_RETURNED`は架空データで埋めません。brokerがその期間を返していない事実として扱います。

## 送っていただくファイル

最初は直近1時間で実行し、作成された次の2ファイルをそのまま送ってください。

- tick CSV
- metadata CSV

Excelで開いて保存し直さないでください。

## エラー時

コンパイルエラーが出た場合は、MetaEditor下部のエラー一覧を省略せず送ってください。

実行後にCSVが無い場合は、MT5の「ツールボックス」→「エキスパート」に表示された次の行を送ってください。

- status
- Range
- Tick file
- Metadata file
- Output folder

## 既存研究との関係

このスクリプトは新候補を作りません。過去成績も変更しません。

Stage273で確認できなかった古いtickを救済する目的ではなく、今後のforward候補についてBid/Askとspreadを狭い時間窓で監査するための収集ツールです。

運用状態は引き続き `NO_LIVE_PROMOTION_AUDIT_ONLY` です。
