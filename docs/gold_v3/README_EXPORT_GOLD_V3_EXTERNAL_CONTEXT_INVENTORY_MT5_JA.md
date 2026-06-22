# ExportGoldV3ExternalContextInventory.mq5 使用手順

## 結論

Stage277で必要な外部sourceのexact broker symbol、M1/M5/M15/H1/H4/D1履歴範囲、server時刻、closed availability、session、spread metadataを一度だけ監査するMQL5スクリプトです。

EAではありません。注文、決済、通知、候補作成、model実行は行いません。

GitHub上の配置:

- `tools/mt5/ExportGoldV3ExternalContextInventory.mq5`
- `tools/gold_v3/stage277_audit_external_context_inventory.py`
- `docs/gold_v3/README_EXPORT_GOLD_V3_EXTERNAL_CONTEXT_INVENTORY_MT5_JA.md`

## 安全契約

- GOLD V3 audit-only
- GOLD V2 / 旧GOLD / DISC8 / Stage41を使用しない
- broker serverのexact symbolだけを記録
- 似たsymbolへの自動置換なし
- Web source fallbackなし
- missing bar補間なし
- nearest futureなし
- broker server bar OPEN時刻のまま保存
- closed barだけをcoverageへ計上
- performance gridなし
- current Specialist Health Router V3変更なし
- phase2 HV retestはSHADOW-only
- live / final signal / MT5注文 / Discord通知 / partial closeはOFF

## MT5への配置

1. リポジトリをPullします。
2. MT5で`F4`を押してMetaEditorを開きます。
3. 「ファイル」→「データフォルダを開く」を選びます。
4. `MQL5/Scripts`を開きます。
5. 次のファイルをコピーします。

   `tools/mt5/ExportGoldV3ExternalContextInventory.mq5`

6. MetaEditorで開き、`F7`でコンパイルします。
7. MT5へ戻り、ナビゲータの「スクリプト」を更新します。
8. `XMTrading-MT5 3`の`GOLD#`チャートへドラッグします。

既存のローソク足取得EAは外しません。このファイルは1回実行型スクリプトです。

## 初回入力値

原則として初期値のまま実行します。

- `InpGoldBaselineSymbol = 空欄`
  - 空欄では現在のchart symbolを使用します。
  - `GOLD#` chartへ置いてください。
- `InpExplicitSymbols = 空欄`
  - exact symbolを追加監査する場合だけ、semicolon区切りで入力します。
  - 推測名を入れません。
- `InpFromServer = 2023.01.01 00:00:00`
- `InpToServerExclusive = 2027.01.01 00:00:00`
- M1 / M5 / M15 / H1 / H4 / D1 = `true`
- `InpUseCommonFolder = false`

scriptはbrokerが返す全symbol名をsymbols CSVへ保存し、priority tokenに一致した候補とGOLD baselineだけを履歴probeします。

source group分類は候補ラベルです。自動採用ではありません。複数候補が出ても削除せず、そのまま送ってください。

履歴probeのため、一時的に対象symbolをMarket Watchへ追加する場合があります。元から非表示だったsymbolはprobe後に元へ戻す処理を行い、restore結果もsymbols CSVへ保存します。

## 出力先

初期設定では現在のMT5端末固有の:

`MQL5/Files`

出力ファイル:

- `gold_v3_stage277_external_context_inventory_symbols.csv`
- `gold_v3_stage277_external_context_inventory_timeframe_coverage.csv`
- `gold_v3_stage277_external_context_inventory_sessions.csv`
- `gold_v3_stage277_external_context_inventory_run_metadata.csv`

## 各CSVの役割

### symbols.csv

- broker上のexact symbol名
- path / description
- currency base / profit / margin
- digits / point
- current spread points
- tick size / tick value / contract size
- source group候補とmatch basis
- Market Watch選択・restore結果

### timeframe_coverage.csv

各exact symbol × timeframeについて:

- 2023〜2026 row数
- first / last bar OPEN時刻
- closed bar rule
- duplicate / non-monotonic
- raw gap count
- CopyRates error
- status

raw gapにはweekendやsession closeを含むため、自動的にmissingとは判定しません。

### sessions.csv

`SymbolInfoSessionTrade`が返したweekday別sessionを保存します。holiday exceptionを推測で補いません。

### run_metadata.csv

- broker company
- account server
- terminal build
- GOLD baseline exact symbol
- requested / effective server range
- safety flags

## 送っていただくファイル

生成された4 CSVをそのまま送ってください。

Excelで開いて保存し直さないでください。

## Python監査

4 CSVを同じfolderへ置いた後の実行例:

```powershell
python tools/gold_v3/stage277_audit_external_context_inventory.py `
  --input-dir "C:\path\to\stage277_raw" `
  --output-dir "docs\gold_v3\stage277_inventory_output" `
  --expected-server "XMTrading-MT5 3" `
  --expected-baseline-symbol "GOLD#"
```

Python監査はsourceをdownloadしません。raw CSVに無いsourceを作りません。

## statusの意味

- `AVAILABLE`: closed barがありCopyRates errorなし
- `PARTIAL_COPY_ERRORS`: rowsはあるが一部chunkでerror
- `NO_RATES_RETURNED`: symbolは存在するがrequested rangeでbarが0
- `COPY_FAILED`: barが0でCopyRates errorあり
- `SYMBOL_SELECT_FAILED`: exact symbolは見えたが履歴probe不可

取得不能を別symbolやWeb sourceで埋めません。

## エラー時

コンパイルエラーが出た場合は、MetaEditor下部のerror一覧を省略せず送ってください。

実行後にCSVが無い場合は、MT5「ツールボックス」→「エキスパート」の末尾にある次の行を送ってください。

- `Stage277 FileOpen failed`
- `Stage277 SymbolSelect failed`
- `Stage277 CopyRates retry`
- `GOLD V3 Stage277 inventory finished`
- `Output folder`

## 現在の正式状態

raw inventoryをまだ受領していない間:

`GOLD_V3_277_EXTERNAL_CAUSAL_CONTEXT_DATA_AVAILABILITY_PARTIAL_PENDING_MT5_EXPORT_AUDIT_ONLY`

運用状態:

`NO_LIVE_PROMOTION_AUDIT_ONLY`
