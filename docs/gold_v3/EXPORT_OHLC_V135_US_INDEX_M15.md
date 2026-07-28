# ExportOhlcToCsv v1.35 — US100Cash / US500Cash M15追加

ユーザー提供の `ExportOhlcToCsv.mq5` v1.34を基準に、次の確定M15足出力を追加する。

- symbol: `US100Cash#`
- file: `us100cashsharp_m15.csv`
- symbol: `US500Cash#`
- file: `us500cashsharp_m15.csv`

## 変更内容

- `InpUs100Symbol` / `InpUs500Symbol`を追加
- `InpExportUs100` / `InpExportUs500`を追加
- M15専用enableと出力ファイル名を追加
- `BuildJobs()`へUS100/US500のM15 jobを追加
- GOLD/BTCの既存job、closed-bar契約、CSV列は変更しない
- `InpIncludeCurrentBar=false`のため、指数も通常はshift=1の確定足を出力する
- 片方の指数symbol名が不正でも、初回成功済みのGOLD/BTC CSVを毎分フル再構築しないよう初期append移行を改善

## 適用

元EAがGitHubに存在しなかったため、次を保存している。

- `patches/ExportOhlcToCsv_v1_34_to_v1_35_us_indices.patch`
- `tools/patch_export_ohlc_us_indices.py`

Windows例:

```powershell
python tools/patch_export_ohlc_us_indices.py "C:\path\to\ExportOhlcToCsv.mq5"
```

同じ場所に`ExportOhlcToCsv.mq5.v1.34.bak`を作成してから、元EAをv1.35へ更新する。

## MT5で確認する項目

EAの入力画面で次を確認する。

```text
InpUs100Symbol = US100Cash#
InpUs500Symbol = US500Cash#
InpExportUs100 = true
InpExportUs500 = true
InpUs100M15Enabled = true
InpUs500M15Enabled = true
InpIncludeCurrentBar = false
```

気配値表示の正式symbol名が異なる場合は、`InpUs100Symbol`または`InpUs500Symbol`だけを実際の名前へ変更する。

## 期待されるFiles直下出力

```text
us100cashsharp_m15.csv
us500cashsharp_m15.csv
```

ヘッダーは既存CSVと同じ。

```text
time,open,high,low,close,tick_volume,spread,real_volume
```

この変更はデータ取得のみで、発注処理は追加しない。
